"""
MIT License

Copyright (c) 2021 CraazzzyyFoxx

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import typing as t


from .exceptions import FiltersError


__all__ = ("Filters",)


class Filters:
    """
    All the filters are optional, and leaving them out of this message will disable them.

    Adding a filter can have adverse effects on performance. These filters force Lavaplayer to decode all audio to PCM, even if the input was already in the Opus format that Discord uses. This means decoding and encoding audio that would normally require very little processing. This is often the case with YouTube videos.
    
    Parameters
    ---------
    volume: :class:`int` | :class:`float`
        Float value where 1.0 is 100%. Values >1.0 may cause clipping
    """
    def __init__(self, volume: t.Union[int, float] = 1.0) -> None:
        self._payload: dict = {"op": "filters", "volume": volume}
    
    def equalizer(self, bands: t.List[t.Dict[int, t.Union[float, int]]]):
        """
        There are 15 bands (0-14) that can be changed.

        "gain" is the multiplier for the given band. The default value is 0. Valid values range from -0.25 to 1.0,
        where -0.25 means the given band is completely muted, and 0.25 means it is doubled. Modifying the gain could
        also change the volume of the output.
        """
        update_list = []
        for x in range(0, len(bands)):
            for key, value in bands[x].items():
                if not -1 < key < 15:
                    raise FiltersError("Invalid band, must be 0-14")
                gain = max(min(float(value), 1.0), -0.25)
                band = key
                update_list.append({'band': band, 'gain': gain})
        self._payload["equalizer"] = update_list
    
    def karaoke(self, level: t.Union[int, float], mono_level: t.Union[int, float], filter_band: t.Union[int, float], filter_width: t.Union[int, float]):
        """
        Uses equalization to eliminate part of a band, usually targeting vocals.
        """
        self._payload["karaoke"] = {"level": level, "monoLevel": mono_level, "filterBand": filter_band, "filterWidth": filter_width}
    
    def timescale(self, speed: t.Union[int, float], pitch: t.Union[int, float], rate: t.Union[int, float]):
        """
        Changes the speed, pitch, and rate. All default to 1.
        """
        self._payload["timescale"] = {"speed": speed, "pitch": pitch, "rate": rate}
    
    def tremolo(self, frequency: t.Union[int, float], depth: t.Union[int, float]):
        """
        Uses amplification to create a shuddering effect, where the volume quickly oscillates.
        Example: https://en.wikipedia.org/wiki/File:Fuse_Electronics_Tremolo_MK-III_Quick_Demo.ogv
        """
        self._payload["tremolo"] = {"frequency": frequency, "depth": depth}
    
    def vibrato(self, frequency: t.Union[int, float], depth: t.Union[int, float]):
        """
        Similar to tremolo. While tremolo oscillates the volume, vibrato oscillates the pitch.
        """
        self._payload["vibrato"] = {"frequency": frequency, "depth": depth}
    
    def rotation(self, rotation_hz: t.Union[int, float]):
        """
        Rotates the sound around the stereo channels/user headphones aka Audio Panning.
        It can produce an effect similar to: https://youtu.be/QB9EB8mTKcc (without the reverb)
        """
        self._payload["rotation"] = {"rotationHz": rotation_hz}

    def distortion(self, sin_offset: t.Union[int, float], sin_scale: t.Union[int, float], cos_offset: t.Union[int, float], cos_scale: t.Union[int, float], tan_offset: t.Union[int, float], tan_scale: t.Union[int, float], offset: t.Union[int, float], scale: t.Union[int, float]):
        """
        Distortion effect. It can generate some pretty unique audio effects.
        """
        self._payload["distortion"] = {"sinOffset": sin_offset, "sinScale": sin_scale, "cosOffset": cos_offset, "cosScale": cos_scale, "tanOffset": tan_offset, "tanScale": tan_scale, "offset": offset, "scale": scale}

    def channel_mix(self, left_to_left: t.Union[int, float], left_to_right: t.Union[int, float], right_to_left: t.Union[int, float], right_to_right: t.Union[int, float]):
        """
        Mixes both channels (left and right), with a configurable factor on how much each channel affects the other.

        With the defaults, both channels are kept independent from each other.

        Setting all factors to 0.5 means both channels get the same audio.
        """
        self._payload["channelMix"] = {"leftToLeft": left_to_left, "leftToRight": left_to_right, "rightToLeft": right_to_left, "rightToRight": right_to_right}

    def low_pass(self, smoothing: t.Union[int, float]):
        """
        Higher frequencies get suppressed, while lower frequencies pass through this filter, thus the name low pass.
        """
        self._payload["lowPass"] = {"smoothing": smoothing}
