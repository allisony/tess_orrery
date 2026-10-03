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

A gif can be created by running

`ffmpeg -framerate 25 -start_number 735 -i movie/fig%04d.png -frames:v 140 \
  -vf "scale=800:-1:flags=lanczos,palettegen=stats_mode=diff" palette.png`

`ffmpeg -framerate 25 -start_number 735 -i movie/fig%04d.png -i palette.png -frames:v 140 \
  -lavfi "scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none" \
  -loop 0 tess_orrery_zoomout.gif`
