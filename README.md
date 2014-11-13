gae-image
=========

Use Google App Engine as a CDN with dynamic image resizing.

The GAE image service can serve as a nice image hosting service. Besides being a CDN, it supports dynamic resizing and cropping of images.

To install:

* install GAE tools on your machine
* create a GAE app on https://appengine.google.com/
* edit app.yaml and resizable-images.yaml and change YOUR_APP to your app id
* edit main.py and change secret to a random string (this is to prevent other people from storing their images in your app)


Once the app is running, you can POST to it with the following parameters:

* image: a URL of the source image
* secret: must match the secret value in main.py
* aspect: if passed, an aspect ratio (as a decimal value) to which the source image will be cropped

The response is a JSON object that contains an [image serving URL](https://cloud.google.com/appengine/docs/python/images/functions#Image_get_serving_url) and the size of the image.
