#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import with_statement

import webapp2
import urllib2
import logging
import json
import base64


from google.appengine.api import files
from google.appengine.api import images
from google.appengine.api import urlfetch
from google.appengine.ext import blobstore

secret = "sasdf43134qwedqerqw1341341"
buf_size = 32 * 1024 * 1024
max_size = 32 * 1024 * 1024

def fetch_image_data_from_url(u):
    res = urlfetch.fetch(u, deadline = 60, method = urlfetch.HEAD)

    if res.status_code != 200:
        logging.error('image url returned %d: %s', res.status_code, u)
        self.abort(400)

    ct = res.headers['Content-Type']
    cl = res.headers['Content-Length']

    if cl != None:
        try:
            cl = int(cl)

            if cl > max_size:
                logging.error('image too large: %s: %d', u, cl)
                self.abort(400)
        except ValueError as e:
            cl = None

    image_data = ""
    offset = 0
    chunk_no = 0

    logging.info("will fetch %s of type %s and size %d", u, ct, cl)

    while offset < cl:
        chunk_end = min(offset + buf_size, cl)
        chunk_res = urlfetch.fetch(u, deadline = 60, headers = {"Range": "bytes=%d-%d" % (offset, chunk_end - 1)})
        image_data = image_data + chunk_res.content
        offset = chunk_end
        chunk_no = chunk_no + 1
        logging.info('fetched %s chunk %d, content is (%s of %d bytes), total fetched %d', u, chunk_no, type(chunk_res.content), len(chunk_res.content), len(image_data))

    # image_data = res.content
    if len(image_data) != cl:
        logging.error("image_data size %d doesn't match content-length %d", len(image_data), cl)
        self.abort(500)

    return image_data

def image_type_stringify(image_format):
    if (image_format == images.JPEG):
        return "jpeg"
    elif (image_format == images.PNG):
        return "png"
    elif (image_format == images.GIF):
        return "gif"
    elif (image_format == images.ICO):
        return "ico"
    elif (image_format == images.WEBP):
        return "webp"
    elif (image_format == images.BMP):
        return "bmp"
    elif (image_format == images.TIFF):
        return "tiff"

def get_image_data(url, data):
    if ((data != None) and (len(data) > 0)):
        image_data = base64.b64decode(data)
    else:
        image_data = fetch_image_data_from_url(url)
    return image_data


class ImageHandler(webapp2.RequestHandler):
    def post(self):
        u = self.request.get('image')
        s = self.request.get('secret')
        n = self.request.get('name')
        data = self.request.get('imageData')
        transform_type = self.request.get('transform')
        aspect = self.request.get('aspect') # width / height
        need_transforms = False

        if secret != s:
            self.abort(403)

        if (aspect is not None) & (aspect != ''):
            aspect = float(aspect)
        else:
            aspect = 0.0

        try:
            image_data = get_image_data(u, data)

            im = images.Image(image_data = image_data)
            input_image_format = image_type_stringify(im.format)
            input_image_aspect = float(im.width) / im.height

            if ((im.format != images.JPEG) and (transform_type != 'NONE')):
                need_transforms = True
                im.im_feeling_lucky()

            if (aspect > 0.0) & (abs(aspect - input_image_aspect) > 0.001):
                need_transforms = True
                left_x = 0.0
                right_x = 1.0
                top_y = 0.0
                bottom_y = 1.0
                if input_image_aspect > aspect:
                    new_aspect = aspect/input_image_aspect
                    left_x = 0.5 - new_aspect/2
                    right_x = 0.5 + new_aspect/2
                else:
                    new_aspect = input_image_aspect/aspect
                    top_y = 0.5 - new_aspect/2
                    bottom_y = 0.5 + new_aspect/2

                logging.info("width %f, height %f, original aspect ratio %f, requested %f, crop ratio %f, cropping to height %f",
                             im.width, im.height,
                             input_image_aspect, aspect, new_aspect,
                             (bottom_y - top_y) * im.height)

                im.crop(left_x, top_y, right_x, bottom_y)


            if need_transforms:
                image_data = im.execute_transforms(output_encoding=images.JPEG, quality = 100)

            im_transform = images.Image(image_data = image_data)
            transform_image_format = image_type_stringify(im_transform.format)

            file_name = files.blobstore.create(mime_type=("image/" + transform_image_format),_blobinfo_uploaded_filename=n)

            with files.open(file_name, 'a') as f:
                f.write(image_data)

            files.finalize(file_name)

            bk = files.blobstore.get_blob_key(file_name)

            logging.info('uploaded: %s -> %s' % (u, bk))

            self.response.content_type = 'application/json'
            self.response.write(json.dumps({
                        "resizableImageUrl": images.get_serving_url(bk),
                        "inputImageFormat": input_image_format,
                        "transformImageFormat": transform_image_format,
                        "width": im.width,
                        "height": im.height
                        }))
        except Exception as e:
            logging.error('error processing %s: %s', u, e)
            self.abort(500)

app = webapp2.WSGIApplication([
    ('/img', ImageHandler),
], debug=True)
