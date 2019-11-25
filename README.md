# Liverpool Telescope facility module for the TOM Toolkit v0.3.0


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
        'tom_observations.facilities.lco.LCOFacility'
        ...
        'tom_lt.lt.LTFacility'
    ]
```

Either directly enter the credentials for your proposal, plus the LT IP address
and Port (see below for how to obtain) into the `tom_lt/lt.py` module;

```python
try:
    import tom_lt.secret
    LT_SETTINGS = tom_lt.secret.LT_SETTINGS
except (ImportError, AttributeError, KeyError):
    LT_SETTINGS = {
        'proposalIDs': (('proposal ID', 'PID1'), ('proposal ID2', 'PID2')),
        'username': 'username',
        'password': 'password'
    }
    LT_HOST = 'LT_IPAddress'
    LT_PORT = 'LT_PortNo'
```

Or create an untracked file called `tom_lt/secret.py` in your TOM to hold the
proposal credentials;

```python
LT_SETTINGS = {
    'proposalIDs': (('proposalID', 'PID'), ),
    'username': 'username',
    'password': 'password'
    LT_HOST = 'LT_IPAddress'
    LT_PORT = 'LT_PortNo'
}
```

**Please refrain from publishing your user credentials, or the LT IP Address to
any public github account**

## Enabling of RTML access for a specifc proposal

The Liverpool Telescope team will need to enable RTML access for the proposal (or proposals)
being used. Please email ltsupport_astronomer@ljmu.ac.uk, to request this, providing details
of the proposal. Once the proposal is enabled for RTML access, we will email you back user
credentials and the required IP Address / Port for connection to the telescope.
