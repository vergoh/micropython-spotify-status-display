# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import re

def wrap(inputstring, width = 70, center = False):
    if inputstring is None:
        return [""]

    output = []
    chunks = inputstring.split(" ")
    o_buffer = ""

    for chunk in chunks:
        if len(o_buffer) == 0:
            if len(chunk) <= width:
                o_buffer = chunk
                continue
        else:
             if len(o_buffer) + len(chunk) + 1 <= width:
                o_buffer = "{} {}".format(o_buffer, chunk)
                continue

        if len(chunk) <= width:
            output.append(o_buffer)
            o_buffer = chunk
            continue

        # force split anything longer than "width"
        while len(chunk):
            if len(o_buffer) == 0:
                space = width
            else:
                space = width - len(o_buffer) - 1

            small_chunk = chunk[:space]
            chunk = chunk[space:]

            if len(o_buffer) == 0:
                output.append(small_chunk)
            else:
                o_buffer = "{} {}".format(o_buffer, small_chunk)
                output.append(o_buffer)
                o_buffer = ""

    if len(o_buffer):
        output.append(o_buffer)

    for i in range(len(output)):
        output[i] = re.sub(r'^- | -$', '', output[i])
        if center:
            output[i] = "{:^{width}}".format(output[i], width=width)

    return output
