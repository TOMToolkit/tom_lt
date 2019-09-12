# Liverpool Telescope facility module for the TOM Toolkit

This module adds [Liverpool Telescope](http://telescope.livjm.ac.uk/) support to the TOM
Toolkit. Using this module TOMs can submit observations to the Liverpool Telescope phase 2
system.

## Installation:

Install the module into your TOM environment:

    pip install tom-lt

Add `tom_lt.lt.LTFacility` to the `TOM_FACILITY_CLASSES` in your TOM's
`settings.py`:

    TOM_FACILITY_CLASSES = [
        'tom_observations.facilities.lco.LCOFacility'
        ...
        'tom_lt.lt.LTFacility'
    ]
