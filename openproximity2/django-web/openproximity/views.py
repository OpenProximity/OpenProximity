# Create your views here.
from django.http import HttpResponse

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import get_template
from django.template import Context
from django.views.generic import list_detail

from re import compile
from mimetypes import guess_type as guess_mime

from models import *
from forms import *
import rpyc
import urllib, os

def add_record_accepted(request):    
    return HttpResponse('Recorded\n')

def add_record(request):
    if not request.method == 'POST':
	raise Http404("I only undertand POST")
    
    print request.POST
    
    time = request.POST.get('time', None)
    address_ = request.POST.get('address', None)
    action_ = request.POST.get('action', None)
    action_extra = request.POST.get('action_extra', None)
    server_address_ = request.POST.get('server_address', None)
    
    if address_ is None or action_ is None:
	raise Http404("Missing required arguments")
    
    record = DeviceRecord()
    record.action = get_object_or_404(RemoteBluetoothAction, short_name=action_)
    
    if server_address_ is not None:
	try:
	    record.dongle = BluetoothDongle.objects.get(address__exact=server_address_)
	except:
	    pass	    
    
    if time is not None:
	record.time = time
    record.address = address_
    record.action_extra = action_extra
    
    record.save()
    
    return HttpResponse('Recorded\n')

AIRCABLE_MAC=['00:50:C2', '00:25:BF']
ADDRESS_MAC=compile("([0-9A-F]{2}\:){5}([0-9A-F]{2})")

def isAIRcable(address):
    return address[:8].upper() in AIRCABLE_MAC
    
def add_dongle(address, name, scanner, uploader, scanner_pri=1, uploader_max=7):
    search=ScannerBluetoothDongle.objects.filter(address=address)
    
    if scanner and search.count()==0:
	rec = ScannerBluetoothDongle()
	rec.address = address
	rec.name = name
	rec.priority = scanner_pri
	rec.enabled = True
	rec.save()
	print rec
    
    if search.count()>0:
	rec=search.get()
	rec.enabled = scanner == True
	rec.save()
    
    search=UploaderBluetoothDongle.objects.filter(address=address)
    
    if uploader and search.count()==0:
	rec = UploaderBluetoothDongle()
	rec.address = address
	rec.name = name
	rec.max_conn = uploader_max
	rec.type = 2
	rec.enabled = True
	rec.save()
	print rec
    
    if search.count()>0:
	rec=search.get()
	rec.enabled = uploader == True
	rec.save()
	print rec
	
def configure_campaign(request, name=None):
    print "configure_campaign", name
    form = CampaignForm()
    print form.as_table()

    return render_to_response('op/campaign_form.html',
	{ 
	    'form':  form,
	})
        
def configure_dongle(request, address=None):
    print "configure_dongle", address
    
    errors = []
    messages = []
    form = None
    if request.method == "POST":
	form=DongleForm(request.POST)
	if form.is_valid():
	    cd=form.cleaned_data
	    add_dongle(
		cd['address'],
	        cd['name'],
		cd["scan"],
		cd["upload"],
		cd["scan_pri"],
		cd["upload_max"],
	    )
	    messages.append("Dongle Configured")

    scanner = None
    scanner_pri = 1
    uploader = None
    uploader_max = 7
    
    name = "OpenProximity 2.0"
    
    search=BluetoothDongle.objects.filter(address=address)
    if search.count()>0:
	name=search.all()[0].name
    
    search=ScannerBluetoothDongle.objects.filter(address=address)
    if search.count() > 0:
	scanner = True
	scanner_pri=search.get().priority
    
    search=UploaderBluetoothDongle.objects.filter(address=address)
    if search.count() > 0:
	uploader = True
	uploader_max=search.get().max_conn

    if form is None:	
	form = DongleForm(
	    initial = {
		'address': address,
    		'name': name,
	        'scan': scanner,
    	        'scan_pri': scanner_pri,
    	        'upload': uploader,
    	        'upload_max': uploader_max,
	    }
	)

    return render_to_response('op/dongle_form.html',
	{ 
	    'form':  form,
	    'messages': messages,
	})
	
def rpc_command(request, command):
    server=rpyc.connect('localhost', 8010)
    func=getattr(server.root, command, None)
    if func is not None:
	rpyc.async(func)()
    
    return HttpResponseRedirect('/')
    
def grab_file(request, file):
    print "grab_file", file
    file = CampaignFile.objects.get(file=file).file
    mime = guess_mime(file.name)
    print mime
    return HttpResponse(file.read(), mimetype=mime[0] )
    
def stats_restart(request):
    RemoteDevice.objects.all().delete()
    return HttpResponseRedirect('/')

LATEST_VERSION_URL="http://proximitymarketing.googlecode.com/svn/trunk/openproximity2/latest-version"

def fetchLatestVersion():
    print "fetchLatestVersion"
    a=urllib.urlopen(LATEST_VERSION_URL)
    version=a.read()
    a.close()
    print version
    return version

def index(request):
    # generate rpc information
    rpc = dict()
    rpc['running'] = None
    try:
	server=rpyc.connect('localhost', 8010)
	rpc['running'] = server is not None
	rpc['uploaders'] = server.root.getUploadersCount()
	rpc['scanners'] = server.root.getScannersCount()
	rpc['dongles'] = list()
	for dongle in server.root.getDongles():
	    a=dict()
	    a['address'] = dongle
	    
	    search = ScannerBluetoothDongle.objects.filter(address=dongle)
	    a['isScanner'] = search.count()>0
	    if search.count()>0:
		a['scan_enabled'] = search.get().enabled == True
		a['scan_pri'] = search.get().priority
	    
	    search = UploaderBluetoothDongle.objects.filter(address=dongle)
	    a['isUploader'] = search.count()>0	    
	    if search.count()>0:
		a['upload_enabled'] = search.get().enabled == True
		a['max_conn'] = search.get().max_conn

	    rpc['dongles'].append(a)
    except Exception, err:
	rpc['error'] = err
	
    # generate stastics information
    stats = dict()
    try:
	stats['seen'] = dict()
	stats['seen']['total'] = RemoteDevice.objects.count()
	stats['seen']['perdongle'] = list()
	for a in ScannerBluetoothDongle.objects.all():
	    b=dict()
	    b['address'] = a.address
	    b['count'] = RemoteBluetoothDeviceFoundRecord.objects.filter(dongle=a).count()
	    stats['seen']['perdongle'].append( b )
	stats['valid'] = RemoteBluetoothDeviceSDP.objects.count()
	stats['accepted'] = RemoteBluetoothDeviceFilesSuccess.objects.count()
	a=RemoteBluetoothDeviceFilesRejected.objects
	for ret in TIMEOUT_RET:
	    a=a.exclude(ret_value=ret)
	stats['rejected'] = a.count()
	stats['timeout'] = RemoteBluetoothDeviceFilesRejected.objects.all().count()-a.count()
	stats['tries'] = RemoteBluetoothDeviceFileTry.objects.count()
    except Exception, err:
	stats['error'] = err
	
    version = dict()
    try:
	version['latest'] = fetchLatestVersion().strip().upper()
	version['current'] = os.environ['OP2_VERSION'].strip().upper()
	version['match'] = version['latest'] == version['current']
    except Exception, err:
	version['error'] = err
	
    return render_to_response("op/index.html",
	{
	    "rpc": rpc,
	    "camps": getMatchingCampaigns(),
	    "stats": stats,
	    "version": version,
	})