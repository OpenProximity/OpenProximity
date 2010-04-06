# -*- coding: utf-8 -*-
import dbus, sys, gobject
from lxml import etree
import logging

logger = logging.getLogger("async_handler")
logger.setLevel(logging.DEBUG)
console=logging.StreamHandler()
logger.addHandler(console)

# channel extractor
CHANNEL_XPATH=etree.XPath("/record/attribute[@id='0x0004']/sequence/sequence/uuid[@value='0x0003']/../uint8/@value")

# state machine 
IDLE = 0
CREATE_DEVICE = 1
FIND_DEVICE = 2
GET_PROPERTIES = 4
DISCOVER_SERVICES = 8
DONE_SDP = 16

# valid uuids
OBEX_UUID='00001105-0000-1000-8000-00805f9b34fb'
FTP_UUID='00001106-0000-1000-8000-00805f9b34fb'

# a helper function don't pay much attention to it
def generate_arguments(*args, **kwargs):
  ''' a function to generate the long list of needed arguments '''
  yield '/usr/bin/obexftp'
  yield '-d'
  yield str(kwargs['dongle'])
  yield '-r'
  yield str(kwargs['retries'])
  if kwargs['service']=='opp':
    yield '-U'
    yield 'none'
    yield '-H'
    yield '-S'
  yield '-T'
  yield str(kwargs['timeout'])
  yield '-b'
  yield str(kwargs['target'])
  yield '-B'
  yield str(kwargs['channel'])
  for f in kwargs['files']:
    yield '-p'
    yield f

class ServiceNotProvided(Exception):
  path = None

  def __init__(self, path, *args, **kwargs):
    super(Exception, self).__init__(*args, **kwargs)
    self.path = path

  def __str__(self):
    return "ServiceNotProvided(%s)" % self.path

class UploadTarget(object):
  ''' 
  A class to represent an upload target.
  This class can handle profile resolving and obex uploading wihtout blocking,
  AKA async. This means that instead of creating X threads to upload to X targets
  you just create X instances of this class.
  
  You need to have a running gobject mainloop for it to work, check the __main__
  for a working example
  '''
  state = None
  dongle = None
  target = None
  device = None
  uuid = None
  bus = None
  connected = False
  reply_callback = None
  error_callback = None

  def __init__(self, dongle, target, bus):
    self.dongle = dongle
    self.target = target
    self.bus = bus
    self.state = IDLE
    path = "%s/dev_%s" % (self.dongle.object_path, self.target.replace(":", "_"))
                                                                                 
    self.bus.add_signal_receiver(self.property_changed_cb, # callback            
        signal_name='PropertyChanged', # signal name                             
        path = path, # filter path                                               
    )  


  def __ReturnError__(self, error):
    if callable(self.error_callback):
      self.error_callback(self, error=error, state=self.state, connected=self.connected)
    self.state = IDLE

  def ResolveChannel(self, uuid, reply_callback, error_callback):
    self.reply_callback = reply_callback
    self.error_callback = error_callback
    self.uuid = uuid
    self.CreateDevice()

  def CreateDevice(self):
    logger.debug("createDevice")
    self.state = CREATE_DEVICE
    self.dongle.CreateDevice(self.target, 
      reply_handler=self.create_device_cb, 
      error_handler=self.create_device_err)

  def property_changed_cb(self, name, value):
    if name.lower() == "connected":
      self.connected = bool(value)
      logger.info("connect %s to %s" % (self.connected, self.target))
  
  def create_device_cb(self, *args, **kwargs):
    logger.debug("create_device_cb %s %s" % ( args, kwargs ) )
    self.FindDevice()

  def create_device_err(self, error):
    logger.debug("create_device_err %s" % error)
    if error.get_dbus_name().lower()!='org.bluez.error.alreadyexists':
      return self.__ReturnError__(error)
    self.FindDevice()
  
  def FindDevice(self):
    logger.debug("findDevice")
    self.state = FIND_DEVICE
    self.dongle.FindDevice(self.target, 
      reply_handler=self.find_device_cb, 
      error_handler=self.find_device_err)

  def find_device_cb(self, path):
    logger.debug("find_device_cb %s" % path)
    self.device = dbus.Interface(self.bus.get_object("org.bluez", path),
				      "org.bluez.Device")
    self.GetProperties()

  def find_device_err(self, error):
    logger.debug("find_device_error %s" % error)
    return self.__ReturnError__(error)

  def GetProperties(self):
    logger.debug("GetProperties")
    self.state = GET_PROPERTIES
    self.device.GetProperties(
      reply_handler = self.get_properties_cb,
      error_handler = self.get_properties_err
    )

  def get_properties_cb(self, properties):
    logger.debug("get_properties_cb %s" % properties)
    if not self.uuid in properties['UUIDs']:
      return self.__ReturnError__(ServiceNotProvided(self.target))
    self.DiscoverServices()

  def get_properties_err(self, error):
    logger.debug("get_properties_err %s" % error)
    return self.__ReturnError__(error)

  def DiscoverServices(self):
    logger.debug("DiscoverServices")
    self.state = DISCOVER_SERVICES
    self.device.DiscoverServices(self.uuid,
      reply_handler = self.discover_services_cb,
      error_handler = self.discover_services_err
    )

  def discover_services_cb(self, services):
    logger.debug("discover_services_cb %s" % services)
    for key in services.keys():
	root=etree.XML(str(services[key]))
	res=CHANNEL_XPATH(root)
	if len(res)>0:
	    return self.FoundService(int(res[0], 16))

  def discover_services_err(self, error):
    logger.debug("discover_services_err %s" % error)
    return self.__ReturnError__(error)

  def FoundService(self, channel):
    logger.info("%s found_channel at %s" %( self.target, channel ))
    self.state = DONE_SDP
    if callable(self.reply_callback):
      self.reply_callback(self, channel)

  def SendFiles(self, files, retries=1, timeout=10, channel=None,
	service='opp', uuid=OBEX_UUID, 
	reply_callback=None, error_callback=None):

    self.reply_callback = reply_callback
    self.error_callback = error_callback

    logger.debug("SendFiles %s %s" % (service, channel) )

    arguments = generate_arguments(
	    dongle=self.dongle.GetProperties()['Address'],
	    retries = retries, timeout = timeout, target = self.target,
	    channel =  channel, files = files, service = service
    )
    b = SpawnAplication(list(arguments))
    b.connect("program-completed", self.send_files_cb)

  def send_files_cb(self, sender, pid, retcode, stdout, stderr):
    if retcode >= 256:
      retcode = retcode / 256
    logger.debug("send_files_cb %s" % retcode)

    if retcode==0 or retcode==255:
      logger.info("file uploaded")
      logger.debug(stdout)
      self.reply_callback(self, stdout, stderr)
    else:
      self.error_callback(target=self, 
	  retcode=retcode, 
	  stdout=stdout, 
	  stderr=stderr,
	  connected=self.connected)
    self.state = IDLE

class SpawnAplication(gobject.GObject):
  ''' 
    A simple class that starts an external application with no stdin
    lets it run, and then when it completes launches a signal
    letting the listeners what was the output of it.
    It needs the gobject event loop to avoid locking
  '''
  # based on http://paste.ubuntu.com/191521/ 

  def __init__(self, argv, now=True):
    super(SpawnAplication, self).__init__()
    self.argv = argv
    if now:
      self.Run()

  def Run(self):
    self.pid, stdin, self.stdout, self.stderr = gobject.spawn_async(
	self.argv,
	flags = gobject.SPAWN_DO_NOT_REAP_CHILD, # make sure we can handle it's exit
	standard_input=False,
	standard_output=True,
	standard_error=True
    )
    gobject.child_watch_add(self.pid, self.__HandleExit)

  def __HandleExit(self, pid, retcode):
    logger.debug("HandleExit pid: %s, recode: %s" % (pid, retcode) )
    
    stdout = gobject.IOChannel(self.stdout).read()
    stderr = gobject.IOChannel(self.stderr).read()
    
    self.emit("program-completed", self.pid, retcode, stdout, stderr)
    return False
        
gobject.signal_new("program-completed", SpawnAplication,
                   gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_INT, gobject.TYPE_INT, 
			gobject.TYPE_STRING, gobject.TYPE_STRING))

def testSpawnApplication():
  def ProgramCompleted(sender, pid, retcode, stdout, stderr):
    import os
    print "ProgramCompleted", pid, retcode, len(stdout.split('\n'))
    os.system("ps -ef | grep %s" % pid)
  
  def testSpawnApplication1():
    print "testSpawnApplication1"
    b = SpawnAplication(['/bin/sleep', '20'], False)
    b.connect("program-completed", ProgramCompleted)
    b.Run()
    print b.pid, b.stdout, b.stderr
    return False

  def testSpawnApplication2():
    print "testSpawnApplication2"
    b = SpawnAplication(['/bin/ls'], False)
    b.connect("program-completed", ProgramCompleted)
    b.Run()
    print b.pid, b.stdout, b.stderr
    return False

  gobject.timeout_add(1, testSpawnApplication1)
  gobject.timeout_add(10, testSpawnApplication2)
  loop.run()

if __name__=='__main__':
  import dbus.glib
  import dbus.mainloop.glib

  logger.setLevel(logging.DEBUG)
  dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
  gobject.threads_init()
  dbus.glib.init_threads()
  loop=gobject.MainLoop()

  if len(sys.argv) < 3:
    print "Usage %s file targets" % sys.argv[0]
    sys.exit(0)

  bus = dbus.SystemBus()
  manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.bluez.Manager")
  adapter = dbus.Interface(bus.get_object("org.bluez", manager.DefaultAdapter()),
							"org.bluez.Adapter")
  files = [ sys.argv[1], ]
  targets = sys.argv[2:]

  def exit(target):
    pending.remove(target)
    if len(pending) == 0:
      print "all work done bye"
      loop.quit()

  def FileUploaded(target, *args, **kwargs):
    print "FileUploaded", args, kwargs
    exit(target)

  def FileFailed(target, *args, **kwargs):
    print "FileFailed", args, kwargs
    exit(target)

  def ChannelResolved(target, channel):
    print "ChannelResolved", channel
    target.SendFiles(channel=channel, files=files, 
	reply_callback=FileUploaded, 
	error_callback=FileFailed)
  
  def ServiceNotProvided(target, error):
    print "ServiceNotProvided", error
    exit(target)

  pending = list()
  for target in targets:
    target = UploadTarget(adapter, target, bus)
    target.ResolveChannel(OBEX_UUID, ChannelResolved, ServiceNotProvided)
    pending.append(target)

  loop.run()
