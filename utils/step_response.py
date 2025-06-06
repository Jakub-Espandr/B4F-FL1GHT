"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

class StepResponseCalculator:
    def __init__(self, time, gyro, p_err, pid_p, axis_name="", threshold=500):
        self.axis_name = axis_name
        self.time = time
        self.gyro = gyro
        self.p_err = p_err
        self.pid_p = pid_p
        self.threshold = threshold
        self.dt = np.mean(np.diff(time))
        self.framelen = 1.0  # seconds
        self.resplen = 0.5   # seconds
        self.cutfreq = 25.0
        self.superpos = 16
        self.window = np.hanning(self._stepcalc(self.framelen))

    def _stepcalc(self, duration):
        freq = 1.0 / self.dt
        arr_len = duration * freq
        return int(arr_len)

    def tukeywin(self, len, alpha=0.5):
        M = len
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

    def winstacker(self, data, flen, superpos):
        tlen = len(self.time)
        shift = int(flen / superpos)
        wins = int(tlen / shift) - superpos
        stack = []
        for i in range(wins):
            stack.append(data[i * shift:i * shift + flen])
        return np.array(stack, dtype=np.float64)

    def wiener_deconvolution(self, input, output, cutfreq):
        pad = 1024 - (len(input[0]) % 1024)
        input = np.pad(input, [[0, 0], [0, pad]], mode='constant')
        output = np.pad(output, [[0, 0], [0, pad]], mode='constant')
        H = np.fft.fft(input, axis=-1)
        G = np.fft.fft(output, axis=-1)
        freq = np.abs(np.fft.fftfreq(len(input[0]), self.dt))
        sn = np.clip(np.abs(freq), cutfreq - 1e-9, cutfreq)
        len_lpf = np.sum(np.ones_like(sn) - sn)
        filt_width = max(1, int(np.round(len_lpf / 6.)))
        sn = gaussian_filter1d(sn, filt_width)
        sn = 10. * (-sn + 1. + 1e-9)
        Hcon = np.conj(H)
        deconvolved_sm = np.real(np.fft.ifft(G * Hcon / (H * Hcon + 1. / sn), axis=-1))
        return deconvolved_sm

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

    def compute(self):
        # Use the original PID-Analyzer formula for pidin
        pidin = self.gyro + self.p_err / (0.032029 * self.pid_p)
        time, input_eq = self.equalize(self.time, pidin)
        time, gyro_eq = self.equalize(self.time, self.gyro)
        self.time = time
        self.input = input_eq
        self.gyro = gyro_eq
        self.flen = self._stepcalc(self.framelen)
        self.rlen = self._stepcalc(self.resplen)
        self.time_resp = self.time[0:self.rlen] - self.time[0]
        # Stack windows
        inp_stack = self.winstacker(self.input, self.flen, self.superpos)
        out_stack = self.winstacker(self.gyro, self.flen, self.superpos)
        window = np.hanning(self.flen)
        inp = inp_stack * window
        outp = out_stack * window
        deconvolved_sm = self.wiener_deconvolution(inp, outp, self.cutfreq)[:, :self.rlen]
        # Calculate max input for thresholding
        max_in = np.max(np.abs(inp), axis=1)
        toolow_mask = (max_in <= 20).astype(float)
        low_mask = (max_in <= self.threshold).astype(float)
        high_mask = (max_in > self.threshold).astype(float)
        # Weighted average and std for low input
        resp_low = self.weighted_mode_avr(deconvolved_sm, low_mask * toolow_mask, [-1.5, 3.5], 1000)
        return {
            'time_resp': self.time_resp,
            'resp_low': resp_low,
            'low_mask': low_mask,
            'toolow_mask': toolow_mask,
            'max_in': max_in,
        } 