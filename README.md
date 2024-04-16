# Liverpool Telescope facility module for the TOM Toolkit


## Features
This module adds [Liverpool Telescope](http://telescope.livjm.ac.uk/) support
to the TOM Toolkit.

The module implements an RTML (Remote Telescope Markup Language) payload which
is sent directly to the Liverpool Telescope. Using this module TOMs can submit
observations to the Liverpool Telescope Phase 2 system. In order to modify or
delete observations, users will need to log in and use the current Phase 2 tool.


#### Currently supported instruments
- IO:O
- IO:I
- SPRAT
- FRODOspec

#### Current feature set
- Setting a window using Flexible time constraint
- Control of all observing constraints (Airmass, Seeing, SkyBrightness)
- Multiband photometry with full IO:O filter set
- Automatic Autoguider usage setting based on exposure time
- Automatic Target Acquisition for SPRAT and FRODOspec instruments
- Paralactic Angled slit orientation for SPRAT
- Automantic Xe Arc calibration frame for SPRAT


#### Unsupported functionality
- Advanced Time constraints (Monitor, Phased, Min. Interval, Fixed)
- Control of Autoguider options
- Performing multiple instrument observations in one scheduled Group
- Defocussing or manual dither / offset patterns
- Manual Cassegrain rotation to achieve specific sky angles
- More specific aquisition routines for SPRAT or FRODOspec


#### Future extentions to the module will enable, in order of planned implementation;
- Cancelling of previously submitted observations
- Checking of an observations status and whether dataproducts are ready
- Ability to pull dataproducts directly into the TOMToolkit for reduction


## Installation and Setup:

Install the module into your TOM environment:

```shell
pip install tom-lt
```

Add `tom_lt.lt.LTFacility` to the `TOM_FACILITY_CLASSES` in your TOM's
`settings.py`:
```python
      TOM_FACILITY_CLASSES = [
        'tom_observations.facilities.lco.LCOFacility',
        ...
        'tom_lt.lt.LTFacility',
    ]
```

Include the following settings inside the `FACILITIES` dictionary inside `settings.py`:

```python
FACILITIES = {
   ...
   'LT': {
           'proposalIDs': (('ProposalID', 'Display Name'), ('ProposalID', 'Display Name')),
           'username': '',
           'password': '',
           'LT_HOST': '',
           'LT_PORT': '',
           'DEBUG': False,
    },
}
```

The proposalIDs key contains a list of proposalIds and the Display name in the TOM Toolkit LT submission form. For one proposal, use a single element list (e.g. `'proposalIDs': (('ProposalID', 'Display Name'),)`

The Liverpool Telescope team will need to enable RTML access for the proposal (or proposals)
being used. Please email ltsupport_astronomer@ljmu.ac.uk, providing details
of your active proposal. Once the proposal is enabled for RTML access, we will email you back user
credentials and the required IP Address / Port for connection to the telescope.


**Please refrain from publishing your user credentials, or the LT IP Address to
any public github account**
