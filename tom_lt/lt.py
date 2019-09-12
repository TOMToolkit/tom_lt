import time

from lxml import etree
from suds import Client
from dateutil.parser import parse
from datetime import datetime

from django import forms
from django.conf import settings
from astropy.coordinates import SkyCoord
from astropy import units as u

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
    project = forms.CharField()
    priority = forms.IntegerField()
    start = forms.CharField(widget=forms.TextInput(attrs={'type': 'date'}))
    end = forms.CharField(widget=forms.TextInput(attrs={'type': 'date'}))
    device = forms.ChoiceField(choices=[('IO:O', 'IO:O')])
    device_type = forms.ChoiceField(choices=[('camera', 'Camera')])
    filter = forms.ChoiceField(choices=[('G', 'G'), ('Z', 'Z')])
    binning = forms.ChoiceField(choices=[('2x2', '2x2')])
    exp_count = forms.IntegerField(min_value=1)
    exp_time = forms.FloatField(min_value=0.1)

    def _build_prolog(self):
        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        uid = 'rtml://rtml-ioo-{}'.format(str(int(time.time())))
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

        device = etree.SubElement(schedule,
                                  'Device',
                                  name=self.cleaned_data['device'],
                                  type=self.cleaned_data['device_type'])
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type=self.cleaned_data['filter'])
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = self.cleaned_data['binning'].split('x')[0]
        etree.SubElement(binning, 'Y', units='pixels').text = self.cleaned_data['binning'].split('x')[1]

        etree.SubElement(schedule, 'Priority').text = str(self.cleaned_data['priority'])

        exposure = etree.SubElement(schedule, 'Exposure', count=str(self.cleaned_data['exp_count']))
        etree.SubElement(exposure, 'Value', units='seconds').text = str(self.cleaned_data['exp_time'])

        date = etree.SubElement(schedule, 'DateTimeConstraint', type='include')
        start = datetime.strftime(parse(self.cleaned_data['start']), '%Y-%m-%dT%H:%M:%s')
        end = datetime.strftime(parse(self.cleaned_data['end']), '%Y-%m-%dT%H:%M:%s')
        etree.SubElement(date, 'DateTimeStart', system='UT', value=start)
        etree.SubElement(date, 'DateTimeEnd', system='UT', value=end)

        return schedule

    def observation_payload(self):
        payload = self._build_prolog()
        payload.append(self._build_project())
        payload.append(self._build_schedule())
        return etree.tostring(payload, encoding="unicode")


class LTFacility(GenericObservationFacility):
    name = 'LT'
    observation_types = [('IMAGING', 'Imaging')]

    def get_form(self, observation_type):
        return LTObservationForm

    def submit_observation(self, observation_payload):
        headers = {
            'Username': LT_SETTINGS['username'],
            'Password': LT_SETTINGS['password']
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http', LT_HOST, LT_PORT)
        client = Client(url=url, headers=headers)
        response = client.service.handle_rtml(observation_payload)
        response_rtml = etree.fromstring(response)
        obs_id = response_rtml.get('uid').split('-')[-1]
        return obs_id

    def cancel_observation(self, observation_id):
        form = self.get_form()()
        payload = form._build_prolog()
        payload.append(form._build_project())

    def validate_observation(self, observation_payload):
        return

    def get_observation_url(self, observation_id):
        return

    def get_terminal_observing_states(self):
        return []

    def get_observing_sites(self):
        return

    def get_observation_status(self):
        return

    def data_products(self, observation_id, product_id=None):
        return
