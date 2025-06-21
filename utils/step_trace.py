"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

class StepTrace:
    framelen = 1.0
    resplen = 0.5
    cutfreq = 25.0
    tuk_alpha = 1.0
    superpos = 16
    threshold = 500.0

    def __init__(self, data):
        self.data = data
        self.input = self.equalize(data['time'], self.pid_in(data['p_err'], data['gyro'], data['P']))[1]
        self.data.update({'input': self.pid_in(data['p_err'], data['gyro'], data['P'])})
        self.equalize_data()
        self.name = self.data['name']
        self.time = self.data['time']
        self.dt = self.time[0] - self.time[1]
        self.input = self.data['input']
        self.gyro = self.data['gyro']
        self.throttle = self.data['throttle']
        self.flen = self.stepcalc(self.time, StepTrace.framelen)
        self.rlen = self.stepcalc(self.time, StepTrace.resplen)
        self.time_resp = self.time[0:self.rlen] - self.time[0]
        self.superpos = StepTrace.superpos
        # Debug windowing parameters
        tlen = len(self.data['time'])
        shift = int(self.flen / self.superpos)
        wins = int(tlen / shift) - self.superpos if shift > 0 else 0
        print(f"[StepTrace DEBUG] tlen={tlen}, flen={self.flen}, superpos={self.superpos}, shift={shift}, wins={wins}")
        self.stacks = self.winstacker({'time':[], 'input':[], 'gyro':[], 'throttle':[]}, self.flen, self.superpos)
        self.window = np.hanning(self.flen)
        self.spec_sm, _, _, self.max_in, _ = self.stack_response(self.stacks, self.window)
        self.low_mask, self.high_mask = self.low_high_mask(self.max_in, self.threshold)
        self.toolow_mask = self.low_high_mask(self.max_in, 20)[1]
        print(f"[StepTrace DEBUG] low_mask len={len(self.low_mask)}, toolow_mask len={len(self.toolow_mask)}, max_in len={len(self.max_in)}")
        print(f"[StepTrace DEBUG] low_mask sum={np.sum(self.low_mask)}, toolow_mask sum={np.sum(self.toolow_mask)}, useful_windows={np.sum(self.low_mask * self.toolow_mask)}")
        self.resp_sm = self.weighted_mode_avr(self.spec_sm, self.toolow_mask, [-1.5,3.5], 1000)
        self.resp_quality = -self.to_mask((np.abs(self.spec_sm - self.resp_sm[0]).mean(axis=1)).clip(0.5-1e-9,0.5)) + 1.
        self.resp_low = self.weighted_mode_avr(self.spec_sm, self.low_mask * self.toolow_mask, [-1.5,3.5], 1000)
        if self.high_mask.sum() > 0:
            self.resp_high = self.weighted_mode_avr(self.spec_sm, self.high_mask * self.toolow_mask, [-1.5,3.5], 1000)
        else:
            self.resp_high = None

    @staticmethod
    def low_high_mask(signal, threshold):
        low = np.copy(signal)
        low[low <= threshold] = 1.
        low[low > threshold] = 0.
        high = -low + 1.
        if high.sum() < 10:
            high *= 0.
        return low, high

    def to_mask(self, clipped):
        clipped -= clipped.min()
        if clipped.max() > 0:
            clipped /= clipped.max()
        return clipped

    def pid_in(self, pval, gyro, pidp):
        pidin = gyro + pval / (0.032029 * pidp)
        return pidin

    def tukeywin(self, length, alpha=0.5):
        M = length
        n = np.arange(M - 1.)
        if alpha <= 0:
            return np.ones(M)
        elif alpha >= 1:
            return np.hanning(M)
        x = np.linspace(0, 1, M, dtype=np.float64)
        w = np.ones(x.shape)
        first_condition = x < alpha / 2
        w[first_condition] = 0.5 * (1 + np.cos(2 * np.pi / alpha * (x[first_condition] - alpha / 2)))
        third_condition = x >= (1 - alpha / 2)
        w[third_condition] = 0.5 * (1 + np.cos(2 * np.pi / alpha * (x[third_condition] - 1 + alpha / 2)))
        return w

    def equalize(self, time, data):
        data_f = interp1d(time, data)
        newtime = np.linspace(time[0], time[-1], len(time), dtype=np.float64)
        return newtime, data_f(newtime)

    def equalize_data(self):
        time = self.data['time']
        newtime = np.linspace(time[0], time[-1], len(time), dtype=np.float64)
        for key in self.data:
            if isinstance(self.data[key], np.ndarray):
                if len(self.data[key]) == len(time):
                    self.data[key] = interp1d(time, self.data[key])(newtime)
        self.data['time'] = newtime

    def stepcalc(self, time, duration):
        tstep = (time[1] - time[0])
        freq = 1. / tstep
        arr_len = duration * freq
        return int(arr_len)

    def winstacker(self, stackdict, flen, superpos):
        tlen = len(self.data['time'])
        shift = int(flen / superpos)
        wins = int(tlen / shift) - superpos
        for i in np.arange(wins):
            for key in stackdict.keys():
                stackdict[key].append(self.data[key][i * shift:i * shift + flen])
        for k in stackdict.keys():
            stackdict[k] = np.array(stackdict[k], dtype=np.float64)
        return stackdict

    def wiener_deconvolution(self, input, output, cutfreq):
        pad = 1024 - (len(input[0]) % 1024)
        input = np.pad(input, [[0,0],[0,pad]], mode='constant')
        output = np.pad(output, [[0,0],[0,pad]], mode='constant')
        H = np.fft.fft(input, axis=-1)
        G = np.fft.fft(output, axis=-1)
        freq = np.abs(np.fft.fftfreq(len(input[0]), self.dt))
        sn = self.to_mask(np.clip(np.abs(freq), cutfreq-1e-9, cutfreq))
        len_lpf = np.sum(np.ones_like(sn) - sn)
        filt_width = max(1, int(np.round(len_lpf / 6.)))
        sn = self.to_mask(gaussian_filter1d(sn, filt_width))
        sn = 10. * (-sn + 1. + 1e-9)
        Hcon = np.conj(H)
        deconvolved_sm = np.real(np.fft.ifft(G * Hcon / (H * Hcon + 1. / sn), axis=-1))
        return deconvolved_sm

    def stack_response(self, stacks, window):
        inp = stacks['input'] * window
        outp = stacks['gyro'] * window
        thr = stacks['throttle'] * window
        deconvolved_sm = self.wiener_deconvolution(inp, outp, self.cutfreq)[:, :self.rlen]
        delta_resp = deconvolved_sm.cumsum(axis=1)
        max_thr = np.abs(np.abs(thr)).max(axis=1)
        avr_in = np.abs(np.abs(inp)).mean(axis=1)
        max_in = np.max(np.abs(inp), axis=1)
        avr_t = stacks['time'].mean(axis=1)
        return delta_resp, avr_t, avr_in, max_in, max_thr

    def weighted_mode_avr(self, values, weights, vertrange, vertbins):
        threshold = 0.5
        filt_width = 7
        resp_y = np.linspace(vertrange[0], vertrange[-1], vertbins, dtype=np.float64)
        times = np.repeat(np.array([self.time_resp], dtype=np.float64), len(values), axis=0)
        weights = np.repeat(weights, len(values[0]))
        hist2d = np.histogram2d(times.flatten(), values.flatten(),
                                range=[[self.time_resp[0], self.time_resp[-1]], vertrange],
                                bins=[len(times[0]), vertbins], weights=weights.flatten())[0].transpose()
        if hist2d.sum():
            hist2d_sm = gaussian_filter1d(hist2d, filt_width, axis=0, mode='constant')
            hist2d_sm /= np.max(hist2d_sm, 0)
            pixelpos = np.repeat(resp_y.reshape(len(resp_y), 1), len(times[0]), axis=1)
            avr = np.average(pixelpos, 0, weights=hist2d_sm * hist2d_sm)
        else:
            hist2d_sm = hist2d
            avr = np.zeros_like(self.time_resp)
        hist2d[hist2d <= threshold] = 0.
        hist2d[hist2d > threshold] = 0.5 / (vertbins / (vertrange[-1] - vertrange[0]))
        std = np.sum(hist2d, 0)
        return avr, std, [self.time_resp, resp_y, hist2d_sm] 