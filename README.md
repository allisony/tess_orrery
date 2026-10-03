# TESS Orrery (after Ethan Kruse's Kepler Orrery)

Adapted kepler_orrery code to create a TESS orrery.

Everything can be run using python assuming the following packages are
installed (most are defaults in every python installation):
* `os`
* `datetime`
* `numpy`
* `matplotlib`
* `glob`

To create the movie or gif from the output series of png files however,
`ffmpeg` must also be installed to run
the `*.sh` files.

All appropriate settings for the movie creation are listed at the top of
`orrery.py` and should be documented.

The movie can be recreated with the default settings by running

`python orrery.py`

`./makeorrery_movie.sh movie/ orrery_movie.mp4 30`

or 

`ffmpeg -framerate 30 -i movie/fig%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 tess_orrery.mp4`
