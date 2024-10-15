import logging
import time

from lxml import etree
from suds import Client

from django import forms
from django.conf import settings

from astropy.coordinates import SkyCoord
from astropy import units as u

from crispy_forms.layout import Layout, Div, HTML
from crispy_forms.bootstrap import PrependedAppendedText, PrependedText

from tom_observations.facility import BaseRoboticObservationForm, BaseRoboticObservationFacility
from tom_targets.models import Target

from tom_lt import __version__

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

try:
    LT_SETTINGS = settings.FACILITIES['LT']
except (AttributeError, KeyError):
    LT_SETTINGS = {
        'proposalIDs': (('proposal ID1', ''), ('proposal ID2', '')),
        'username': '',
        'password': '',
        'LT_HOST': '',
        'LT_PORT': '',
        'DEBUG': False,
    }


LT_XML_NS = 'http://www.rtml.org/v3.1a'
LT_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
LT_SCHEMA_LOCATION = 'http://www.rtml.org/v3.1a http://telescope.livjm.ac.uk/rtml/RTML-nightly.xsd'


class LTObservationForm(BaseRoboticObservationForm):
    project = forms.ChoiceField(choices=LT_SETTINGS['proposalIDs'], label='Proposal')

    startdate = forms.CharField(label='Start Date',
                                widget=forms.TextInput(attrs={'type': 'date'}))
    starttime = forms.CharField(label='Time',
                                widget=forms.TextInput(attrs={'type': 'time'}),
                                initial='12:00')
    enddate = forms.CharField(label='End Date',
                              widget=forms.TextInput(attrs={'type': 'date'}))
    endtime = forms.CharField(label='Time',
                              widget=forms.TextInput(attrs={'type': 'time'}),
                              initial='12:00')

    max_airmass = forms.FloatField(min_value=1, max_value=3, initial=2,
                                   label='Constraints',
                                   widget=forms.NumberInput(attrs={'step': '0.1'}))
    max_seeing = forms.FloatField(min_value=1, max_value=5, initial=1.2,
                                  widget=forms.NumberInput(attrs={'step': '0.1'}),
                                  label='')
    max_skybri = forms.FloatField(min_value=0, max_value=10, initial=1,
                                  widget=forms.NumberInput(attrs={'step': '0.1'}),
                                  label='Sky Brightness Maximum')
    photometric = forms.ChoiceField(choices=[('clear', 'Yes'), ('light', 'No')], initial='light')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            self.layout(),
            self.extra_layout(),
            self.button_layout(),
            self.version_layout(),
        )

    def is_valid(self):
        super().is_valid()
        errors = LTFacility.validate_observation(self, self.observation_payload())
        if errors:
            self.add_error(None, errors)
        return not errors

    def layout(self):
        return Div(
            Div(
                Div(
                    'project',
                    css_class='form-row'
                ),
                Div(
                    'startdate', 'starttime',
                    css_class='form-row'
                ),
                Div(
                    'enddate', 'endtime',
                    css_class='form-row'
                ),
                css_class='col-md-16'
            ),
            Div(
                Div(css_class='col-md-2'),
                Div(
                    PrependedText('max_airmass', 'Airmass <'),
                    PrependedAppendedText('max_seeing', 'Seeing <', 'arcsec'),
                    PrependedAppendedText('max_skybri', 'Dark + ', 'mag/arcsec\xB2'),
                    'photometric',
                    css_class='col-md-8'
                ),
                css_class='form-row'
            ),
            HTML('<hr width="85%"><h4>Instrument Config</h4>'),
            css_class='form-row'
        )

    def version_layout(self):
        return Div(HTML('<hr>'
                        '<em><a href="http://telescope.livjm.ac.uk" target="_blank">Liverpool Telescope</a>'
                        ' Facility module v{{version}}</em>'
                        ))

    def extra_layout(self):
        return Div()

    def _build_prolog(self):
        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        uid = format(str(int(time.time())))
        return etree.Element('RTML', {schemaLocation: LT_SCHEMA_LOCATION}, xmlns=LT_XML_NS,
                             mode='request', uid=uid, version='3.1a', nsmap=namespaces)

    def _build_project(self, payload):
        project = etree.Element('Project', ProjectID=self.cleaned_data['project'])
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = LT_SETTINGS['username']
        etree.SubElement(contact, 'Name').text = ''
        payload.append(project)

    def _build_constraints(self):
        airmass_const = etree.Element('AirmassConstraint', maximum=str(self.cleaned_data['max_airmass']))

        sky_const = etree.Element('SkyConstraint')
        etree.SubElement(sky_const, 'Flux').text = str(self.cleaned_data['max_skybri'])
        etree.SubElement(sky_const, 'Units').text = 'magnitudes/square-arcsecond'

        seeing_const = etree.Element('SeeingConstraint',
                                     maximum=(str(self.cleaned_data['max_seeing'])),
                                     units='arcseconds')

        photom_const = etree.Element('ExtinctionConstraint')
        etree.SubElement(photom_const, 'Clouds').text = self.cleaned_data['photometric']

        date_const = etree.Element('DateTimeConstraint', type='include')
        start = self.cleaned_data['startdate'] + 'T' + self.cleaned_data['starttime'] + ':00+00:00'
        end = self.cleaned_data['enddate'] + 'T' + self.cleaned_data['endtime'] + ':00+00:00'
        etree.SubElement(date_const, 'DateTimeStart', system='UT', value=start)
        etree.SubElement(date_const, 'DateTimeEnd', system='UT', value=end)

        return [airmass_const, sky_const, seeing_const, photom_const, date_const]

    def _build_target(self):
        target_to_observe = Target.objects.get(pk=self.cleaned_data['target_id'])

        target = etree.Element('Target', name=target_to_observe.name)
        c = SkyCoord(ra=target_to_observe.ra*u.degree, dec=target_to_observe.dec*u.degree)
        coordinates = etree.SubElement(target, 'Coordinates')
        ra = etree.SubElement(coordinates, 'RightAscension')
        etree.SubElement(ra, 'Hours').text = str(int(c.ra.hms.h))
        etree.SubElement(ra, 'Minutes').text = str(int(c.ra.hms.m))
        etree.SubElement(ra, 'Seconds').text = str(c.ra.hms.s)

        dec = etree.SubElement(coordinates, 'Declination')
        sign = '+' if c.dec.signed_dms.sign == 1.0 else '-'
        etree.SubElement(dec, 'Degrees').text = sign + str(int(c.dec.signed_dms.d))
        etree.SubElement(dec, 'Arcminutes').text = str(int(c.dec.signed_dms.m))
        etree.SubElement(dec, 'Arcseconds').text = str(c.dec.signed_dms.s)
        etree.SubElement(coordinates, 'Equinox').text = str(target_to_observe.epoch)
        return target

    def observation_payload(self):
        payload = self._build_prolog()
        self._build_project(payload)
        self._build_inst_schedule(payload)
        return etree.tostring(payload, encoding="unicode")


class LT_IOO_ObservationForm(LTObservationForm):
    binning = forms.ChoiceField(
        choices=[('1x1', '1x1'), ('2x2', '2x2')],
        initial=('2x2', '2x2'),
        help_text='2x2 binning is usual, giving 0.3 arcsec/pixel, \
                   faster readout and lower readout noise. 1x1 binning should \
                   only be selected if specifically required.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = ('U',
                        'R',
                        'G',
                        'I',
                        'Z',
                        'B',
                        'V',
                        'Halpha6566',
                        'Halpha6634',
                        'Halpha6705',
                        'Halpha6755',
                        'Halpha6822')

        for filter in self.filters:
            if filter == self.filters[0]:
                self.fields['exp_time_' + filter] = forms.FloatField(min_value=0,
                                                                     initial=120,
                                                                     label='Integration Time')
                self.fields['exp_count_' + filter] = forms.IntegerField(min_value=0,
                                                                        initial=0,
                                                                        label='No. of integrations')
            else:
                self.fields['exp_time_' + filter] = forms.FloatField(min_value=0,
                                                                     initial=120,
                                                                     label='')
                self.fields['exp_count_' + filter] = forms.IntegerField(min_value=0,
                                                                        initial=0,
                                                                        label='')

    def extra_layout(self):
        return Div(
            Div(
                Div(HTML('<br><h5>Sloan</h5>'), css_class='form_row'),
                Div(
                    Div(PrependedAppendedText('exp_time_U', 'u\'', 's'),
                        PrependedAppendedText('exp_time_G', 'g\'', 's'),
                        PrependedAppendedText('exp_time_R', 'r\'', 's'),
                        PrependedAppendedText('exp_time_I', 'i\'', 's'),
                        PrependedAppendedText('exp_time_Z', 'z\'', 's'),
                        css_class='col-md-6', ),

                    Div('exp_count_U',
                        'exp_count_G',
                        'exp_count_R',
                        'exp_count_I',
                        'exp_count_Z',
                        css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(HTML('<br><h5>Bessell</h5>'), css_class='form_row'),
                Div(
                    Div(PrependedAppendedText('exp_time_B', 'B', 's'),
                        PrependedAppendedText('exp_time_V', 'V', 's'),
                        css_class='col-md-6', ),

                    Div('exp_count_B',
                        'exp_count_V',
                        css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(HTML('<br><h5>H-alpha</h5>'), css_class='form_row'),

                Div(
                    Div(PrependedAppendedText('exp_time_Halpha6566', '6566', 's'),
                        PrependedAppendedText('exp_time_Halpha6634', '6634', 's'),
                        PrependedAppendedText('exp_time_Halpha6705', '6705', 's'),
                        PrependedAppendedText('exp_time_Halpha6755', '6755', 's'),
                        PrependedAppendedText('exp_time_Halpha6822', '6822', 's'),
                        css_class='col-md-6', ),

                    Div('exp_count_Halpha6566',
                        'exp_count_Halpha6634',
                        'exp_count_Halpha6705',
                        'exp_count_Halpha6755',
                        'exp_count_Halpha6822',
                        css_class='col-md-6'),
                    css_class='form-row'
                    ),
                css_class='col-md-6'
            ),
            Div(css_class='col-md-1'),
            Div(
                Div('binning', css_class='col-md-6'),
                css_class='col'
            ),
            css_class='form-row'
        )

    def _build_inst_schedule(self, payload):

        for filter in self.filters:
            if self.cleaned_data['exp_count_' + filter] != 0:
                payload.append(self._build_schedule(filter))

    def _build_schedule(self, filter):
        exp_time = self.cleaned_data['exp_time_' + filter]
        exp_count = self.cleaned_data['exp_count_' + filter]

        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="IO:O", type="camera")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type=filter)
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = self.cleaned_data['binning'].split('x')[0]
        etree.SubElement(binning, 'Y', units='pixels').text = self.cleaned_data['binning'].split('x')[1]
        exposure = etree.SubElement(schedule, 'Exposure', count=str(exp_count))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(exp_time)
        schedule.append(self._build_target())
        for const in self._build_constraints():
            schedule.append(const)
        return schedule


class LT_IOI_ObservationForm(LTObservationForm):
    exp_time = forms.FloatField(min_value=0, initial=120, label='Integration time',
                                widget=forms.NumberInput(attrs={'step': '0.1'}))
    exp_count = forms.IntegerField(min_value=1, initial=5, label='No. of integrations',
                                   help_text='The Liverpool Telescope will automatically \
                                   create a dither pattern between exposures.')

    def extra_layout(self):
        return Div(
            Div(
                Div(
                    Div(PrependedAppendedText('exp_time', 'H', 's'), css_class='col-md-6'),
                    Div('exp_count', css_class='col-md-6'),
                    css_class='form-row'
                ),
                css_class='col-md-6'
            ),
            Div(css_class='col-md-5'),

            css_class='form-row'
        )

    def _build_inst_schedule(self, payload):
        exp_time = self.cleaned_data['exp_time']
        exp_count = self.cleaned_data['exp_count']

        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="IO:I", type="camera")
        etree.SubElement(device, 'SpectralRegion').text = 'infrared'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type='H')
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = '1'
        etree.SubElement(binning, 'Y', units='pixels').text = '1'
        exposure = etree.SubElement(schedule, 'Exposure', count=str(exp_count))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(exp_time)
        schedule.append(self._build_target())
        for const in self._build_constraints():
            schedule.append(const)
        payload.append(schedule)


class LT_SPRAT_ObservationForm(LTObservationForm):
    exp_time = forms.FloatField(min_value=0, initial=120, label='Integration time',
                                widget=forms.NumberInput(attrs={'step': '0.1'}))
    exp_count = forms.IntegerField(min_value=1, initial=1, label='No. of integrations')

    grating = forms.ChoiceField(choices=[('red', 'Red'), ('blue', 'Blue')], initial='red')

    def extra_layout(self):
        return Div(
                    Div(PrependedAppendedText('exp_time', 'SPRAT', 's'), css_class='col'),
                    Div('exp_count', css_class='col'),
                    Div('grating', css_class='col'),
                    css_class='form-row'
                    )

    def _build_inst_schedule(self, payload):
        exp_time = self.cleaned_data['exp_time']
        exp_count = self.cleaned_data['exp_count']
        grating = self.cleaned_data['grating']

        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="Sprat", type="spectrograph")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Grating', name=grating)
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = '1'
        etree.SubElement(binning, 'Y', units='pixels').text = '1'
        exposure = etree.SubElement(schedule, 'Exposure', count=str(exp_count))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(exp_time)
        schedule.append(self._build_target())
        for const in self._build_constraints():
            schedule.append(const)
        payload.append(schedule)


class LT_FRODO_ObservationForm(LTObservationForm):
    exp_time_blue = forms.FloatField(min_value=0, initial=120, label='Integration time',
                                     widget=forms.NumberInput(attrs={'step': '0.1'}))
    exp_count_blue = forms.IntegerField(min_value=0, initial=1, label='No. of integrations')
    res_blue = forms.ChoiceField(choices=[('high', 'High'), ('low', 'Low')], initial='low', label='Resolution')

    exp_time_red = forms.FloatField(min_value=0, initial=120, label='',
                                    widget=forms.NumberInput(attrs={'step': '0.1'}))
    exp_count_red = forms.IntegerField(min_value=0, initial=1, label='')
    res_red = forms.ChoiceField(choices=[('high', 'High'), ('low', 'Low')], initial='low', label='')

    def extra_layout(self):
        return Div(
                    Div(PrependedAppendedText('exp_time_blue', 'Blue Arm', 's'),
                        PrependedAppendedText('exp_time_red', 'Red Arm', 's'),
                        css_class='col'),
                    Div('exp_count_blue', 'exp_count_red', css_class='col'),
                    Div('res_blue', 'res_red', css_class='col'),
                    css_class='form-row'
        )

    def _build_inst_schedule(self, payload):
        payload.append(self._build_schedule('FrodoSpec-Blue',
                                            str(self.cleaned_data['res_blue']),
                                            str(self.cleaned_data['exp_count_blue']),
                                            str(self.cleaned_data['exp_time_blue'])))
        payload.append(self._build_schedule('FrodoSpec-Red',
                                            str(self.cleaned_data['res_red']),
                                            str(self.cleaned_data['exp_count_red']),
                                            str(self.cleaned_data['exp_time_red'])))

    def _build_schedule(self, device, grating, exp_count, exp_time):
        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name=device, type="spectrograph")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Grating', name=grating)
        exposure = etree.SubElement(schedule, 'Exposure', count=exp_count)
        etree.SubElement(exposure, 'Value', units='seconds').text = exp_time
        schedule.append(self._build_target())
        for const in self._build_constraints():
            schedule.append(const)
        return schedule


class LTFacility(BaseRoboticObservationFacility):
    name = 'LT'
    observation_types = [('IOO', 'IO:O'), ('IOI', 'IO:I'), ('SPRAT', 'SPRAT'), ('FRODO', 'FRODOSpec')]

    # observation_forms should be a dictionary
    #  * it's .items() method is called in views.py::ObservationCreateView.get_context_data()
    #  * the keys are the observation_types; values are the ObservationForm classes

    # TODO: this (required) addition seems redudant to the get_form() method below.
    # TODO: see how get_form() is used and if it's still required
    observation_forms = {
        'IOO': LT_IOO_ObservationForm,
        'IOI': LT_IOI_ObservationForm,
        'SPRAT': LT_SPRAT_ObservationForm,
        'FRODO': LT_FRODO_ObservationForm
    }

    SITES = {
            'La Palma': {
                'sitecode': 'orm',  # TODO: what does this mean? and document it.
                'latitude': 28.762,
                'longitude': -17.872,
                'elevation': 2363}
            }

    def get_form(self, observation_type):
        """
        """
        try:
            return self.observation_forms[observation_type]
        except KeyError:
            return self.observation_forms['IOO']
        # This is the original implementation of this method below.
        # I've rewritten it to use the observation_forms dictionary above.
        #
        # if observation_type == 'IOO':
        #     return LT_IOO_ObservationForm
        # elif observation_type == 'IOI':
        #     return LT_IOI_ObservationForm
        # elif observation_type == 'SPRAT':
        #     return LT_SPRAT_ObservationForm
        # elif observation_type == 'FRODO':
        #     return LT_FRODO_ObservationForm
        # else:
        #     return LT_IOO_ObservationForm

    def get_facility_context_data(self, **kwargs):
        """Provide Facility-specific data to context for ObservationCreateView's template

        This method is called by ObservationCreateView.get_context_data() and returns a
        dictionary of context data to be added to the View's context
        """
        facility_context_data = super().get_facility_context_data(**kwargs)
        new_context_data = {
            'version': __version__,  # from tom_tl/__init__.py
        }

        facility_context_data.update(new_context_data)
        return facility_context_data

    def submit_observation(self, observation_payload):
        if (LT_SETTINGS['DEBUG']):
            payload = etree.fromstring(observation_payload)
            f = open("created.rtml", "w")
            f.write(etree.tostring(payload, encoding="unicode", pretty_print=True))
            f.close()
            return [0]
        else:
            headers = {
                'Username': LT_SETTINGS['username'],
                'Password': LT_SETTINGS['password']
            }
            url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http', LT_SETTINGS['LT_HOST'],
                                                                     LT_SETTINGS['LT_PORT'])
            client = Client(url=url, headers=headers)
            # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
            response = client.service.handle_rtml(observation_payload).replace('encoding="ISO-8859-1"', '')
            response_rtml = etree.fromstring(response)
            mode = response_rtml.get('mode')
            if mode == 'reject':
                self.dump_request_response(observation_payload, response_rtml)
            obs_id = response_rtml.get('uid')
            return [obs_id]

    def cancel_observation(self, observation_id):
        form = self.get_form()()
        payload = form._build_prolog()
        payload.append(form._build_project())

    def validate_observation(self, observation_payload):
        if (LT_SETTINGS['DEBUG']):
            return []
        else:
            headers = {
                'Username': LT_SETTINGS['username'],
                'Password': LT_SETTINGS['password']
            }
            url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http',
                                                                     LT_SETTINGS['LT_HOST'],
                                                                     LT_SETTINGS['LT_PORT'])
            client = Client(url=url, headers=headers)
            validate_payload = etree.fromstring(observation_payload)
            # Change the payload to an inquiry mode document to test connectivity.
            validate_payload.set('mode', 'inquiry')
            # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
            try:
                response = client.service.handle_rtml(validate_payload).replace('encoding="ISO-8859-1"', '')
            except Exception as e:
                return [f'Error with connection to Liverpool Telescope: {e}',
                        'This could be due to incorrect credentials, or IP / Port settings',
                        'Occassionally, this could be due to the rebooting of systems at the Telescope Site',
                        'Please retry at another time.',
                        'If the problem persists please contact ltsupport_astronomer@ljmu.ac.uk']

            response_rtml = etree.fromstring(response)
            if response_rtml.get('mode') == 'offer':
                return []
            elif response_rtml.get('mode') == 'reject':
                return ['Error with RTML submission to Liverpool Telescope',
                        'This can occassionally happen due to systems rebooting at the Telescope Site',
                        'Please retry at another time.',
                        'If the problem persists please contact ltsupport_astronomer@ljmu.ac.uk']

    def get_observation_url(self, observation_id):
        return ''

    def get_terminal_observing_states(self):
        return ['IN_PROGRESS', 'COMPLETED']

    def get_observing_sites(self):
        return self.SITES

    def get_observation_status(self, observation_id):
        return

    def data_products(self, observation_id, product_id=None):
        return []
