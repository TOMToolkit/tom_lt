import time

from lxml import etree
from suds import Client
from dateutil.parser import parse
from datetime import datetime

from django import forms
from django.conf import settings
from astropy.coordinates import SkyCoord
from astropy import units as u

from crispy_forms.layout import Layout, Div, HTML
from crispy_forms.bootstrap import PrependedAppendedText, PrependedText, InlineRadios

from tom_observations.facility import GenericObservationForm, GenericObservationFacility
from tom_targets.models import Target

# Determine settings for this module
try:
    LT_SETTINGS = settings.FACILITIES['LT']
except (AttributeError, KeyError):
    LT_SETTINGS = {
        'proposal': '',
        'username': '',
        'password': ''
    }

LT_HOST = '161.72.57.3'
LT_PORT = '8080'
LT_XML_NS = 'http://www.rtml.org/v3.1a'
LT_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
LT_SCHEMA_LOCATION = 'http://www.rtml.org/v3.1a http://telescope.livjm.ac.uk/rtml/RTML-nightly.xsd'


class LTObservationForm(GenericObservationForm):

    project = forms.CharField(initial='project')
    priority = forms.IntegerField(min_value=1, max_value=3, initial=1)

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
    max_seeing = forms.FloatField(min_value=0.5, max_value=3, initial=1.2,
                                  widget=forms.NumberInput(attrs={'step': '0.1'}),
                                  label='')
    max_skybri = forms.FloatField(min_value=0, max_value=10, initial=1,
                                  widget=forms.NumberInput(attrs={'step': '0.1'}),
                                  label='')
    photometric = forms.ChoiceField(choices=[('clear', 'Yes'), ('', 'No')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            self.layout(),
            self.extra_layout()
        )

    def layout(self):
        return Div(
            Div(
                Div(
                    'project', 'startdate', 'enddate',
                    css_class='col-md-6'
                ),
                Div(
                    'priority', 'starttime', 'endtime',
                    css_class='col-md-6'
                ),
                css_class='form-row'
            ),
            Div(
                Div(css_class='col-md-2'),
                Div(
                    PrependedText('max_airmass', 'Airmass <'),
                    PrependedAppendedText('max_seeing', 'Seeing <', 'arcsec'),
                    PrependedAppendedText('max_skybri', 'SkyBrightness <', 'mag/arcsec'),
                    InlineRadios('photometric'),
                    css_class='col'
                ),
                css_class='form-row'
            ),
            HTML('<hr width="85%">'),
            css_class='form-row'
        )

    def extra_layout(self):
        return Div()

    def _build_prolog(self):
        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        uid = 'DJANGO'.format(str(int(time.time())))
        return etree.Element('RTML', {schemaLocation: LT_SCHEMA_LOCATION}, xmlns=LT_XML_NS,
                             mode='request', uid=uid, version='3.1a', nsmap=namespaces)

    def _build_project(self):
        project = etree.Element('Project', ProjectID=LT_SETTINGS['proposal'])
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = LT_SETTINGS['username']
        etree.SubElement(contact, 'Name').text = ''
        return project

    def _build_schedule(self):
        target_to_observe = Target.objects.get(pk=self.cleaned_data['target_id'])

        schedule = etree.Element('Schedule')

        target = etree.SubElement(schedule, 'Target', name=target_to_observe.name)
        c = SkyCoord(ra=target_to_observe.ra*u.degree, dec=target_to_observe.dec*u.degree)
        coordinates = etree.SubElement(target, 'Coordinates')
        ra = etree.SubElement(coordinates, 'RightAscension')
        etree.SubElement(ra, 'Hours').text = str(int(c.ra.hms.h))
        etree.SubElement(ra, 'Minutes').text = str(int(c.ra.hms.m))
        etree.SubElement(ra, 'Seconds').text = str(c.ra.hms.s)

        dec = etree.SubElement(coordinates, 'Declination')
        sign = '+' if c.dec.signed_dms.sign == '1.0' else '-'
        etree.SubElement(dec, 'Degrees').text = sign + str(int(c.dec.signed_dms.d))
        etree.SubElement(dec, 'Arcminutes').text = str(int(c.dec.signed_dms.m))
        etree.SubElement(dec, 'Arcseconds').text = str(c.dec.signed_dms.s)
        etree.SubElement(coordinates, 'Equinox').text = target_to_observe.epoch

        self._build_instconfig(schedule)

        date = etree.SubElement(schedule, 'DateTimeConstraint', type='include')
        start = self.cleaned_data['startdate'] + 'T' + self.cleaned_data['starttime'] + ':00+00:00'
        end = self.cleaned_data['enddate'] + 'T' + self.cleaned_data['endtime'] + ':00+00:00'
        etree.SubElement(date, 'DateTimeStart', system='UT', value=start)
        etree.SubElement(date, 'DateTimeEnd', system='UT', value=end)
        return schedule

    def observation_payload(self):
        payload = self._build_prolog()
        payload.append(self._build_project())
        payload.append(self._build_schedule())
        print(etree.tostring(payload, encoding="unicode", pretty_print=True))
        return etree.tostring(payload, encoding="unicode")


class LT_IOO_ObservationForm(LTObservationForm):
    exposure_count_u = forms.IntegerField(min_value=0, initial=0, label='No. of exposures')
    exposure_time_u = forms.FloatField(min_value=0, initial=300, label='Exposure time',
                                       widget=forms.NumberInput(attrs={'step': '0.1'}))
    exposure_count_g = forms.IntegerField(min_value=0, initial=0, label='')
    exposure_time_g = forms.FloatField(min_value=0, initial=200, label='',
                                       widget=forms.NumberInput(attrs={'step': '0.1'}))
    exposure_count_r = forms.IntegerField(min_value=0, initial=0, label='')
    exposure_time_r = forms.FloatField(min_value=0, initial=120, label='',
                                       widget=forms.NumberInput(attrs={'step': '0.1'}))
    exposure_count_i = forms.IntegerField(min_value=0, initial=0, label='')
    exposure_time_i = forms.FloatField(min_value=0, initial=200, label='',
                                       widget=forms.NumberInput(attrs={'step': '0.1'}))
    exposure_count_z = forms.IntegerField(min_value=0, initial=0, label='')
    exposure_time_z = forms.FloatField(min_value=0, initial=120, label='',
                                       widget=forms.NumberInput(attrs={'step': '0.1'}))
    binning = forms.ChoiceField(choices=[('1x1', '1x1'), ('2x2', '2x2')], initial=('2x2', '2x2'))

    def extra_layout(self):
        return Div(
            Div(

                Div(
                    Div(PrependedText('exposure_time_u', 'u\''), css_class='col-md-6'),
                    Div('exposure_count_u', css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(
                    Div(PrependedText('exposure_time_g', 'g\''), css_class='col-md-6'),
                    Div('exposure_count_g', css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(
                    Div(PrependedText('exposure_time_r', 'r\''), css_class='col-md-6'),
                    Div('exposure_count_r', css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(
                    Div(PrependedText('exposure_time_i', 'i\''), css_class='col-md-6'),
                    Div('exposure_count_i', css_class='col-md-6'),
                    css_class='form-row'
                ),
                Div(
                    Div(PrependedText('exposure_time_z', 'z\''), css_class='col-md-6'),
                    Div('exposure_count_z', css_class='col-md-6'),
                    css_class='form-row'
                ),
                css_class='col'
            ),
            Div(css_class='col-md-1'),
            Div('binning', css_class='col'),
            css_class='form-row'
        )

    def _inst_config(self, schedule):
        device = etree.SubElement(schedule, 'Device', name="IO:O", type="camera")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type=self.cleaned_data['filter'])
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = self.cleaned_data['binning'].split('x')[0]
        etree.SubElement(binning, 'Y', units='pixels').text = self.cleaned_data['binning'].split('x')[1]
        exposure = etree.SubElement(schedule, 'Exposure', count=str(self.cleaned_data['expcount']))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(self.cleaned_data['exptime'])


class LT_IOI_ObservationForm(LTObservationForm):
    IOI1 = forms.CharField(initial='one')
    IOI2 = forms.CharField(initial='two')

    def extra_layout(self):
        return Div(
            Div(
                'IOI1',
                css_class='col'
            ),
            Div(
                'IOI2',
                css_class='col'
            ),
            css_class='form-row'
        )


class LT_SPRAT_ObservationForm(LTObservationForm):
    pass



class LT_FRODO_ObservationForm(LTObservationForm):
    pass



class LTFacility(GenericObservationFacility):
    name = 'LT'
    observation_types = [('IOO', 'IO:O'), ('IOI', 'IO:I'), ('SPRAT', 'Sprat'), ('FRODO', 'Frodo')]

    SITES = {
            'La Palma': {
                'sitecode': 'orm',
                'latitude': 28.762,
                'longitude': -17.872,
                'elevation': 2363}
            }

    def get_form(self, observation_type):
        if observation_type == 'IOO':
            return LT_IOO_ObservationForm
        elif observation_type == 'IOI':
            return LT_IOI_ObservationForm
        elif observation_type == 'SPRAT':
            return LT_SPRAT_ObservationForm
        elif observation_type == 'FRODO':
            return LT_FRODO_ObservationForm
        else:
            return LT_IOO_ObservationForm

    def submit_observation(self, observation_payload):
        print("HERE")
        headers = {
            'Username': LT_SETTINGS['username'],
            'Password': LT_SETTINGS['password']
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http', LT_HOST, LT_PORT)
        client = Client(url=url, headers=headers)

        response = client.service.handle_rtml(observation_payload)
        response_rtml = etree.fromstring(response)
        obs_id = response_rtml.get('uid').split('-')[-1]
        return [obs_id]

    def cancel_observation(self, observation_id):
        form = self.get_form()()
        payload = form._build_prolog()
        payload.append(form._build_project())

    def validate_observation(self, observation_payload):
        return

    def get_observation_url(self, observation_id):
        return ''

    def get_terminal_observing_states(self):
        return ['IN_PROGRESS', 'COMPLETED']

    def get_observing_sites(self, observation_id):
        return self.SITES

    def get_observation_status(self, observation_id):
        return

    def data_products(self, observation_id, product_id=None):
        return []
