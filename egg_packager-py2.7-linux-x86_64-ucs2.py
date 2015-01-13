#!/usr/bin/env python

# Configure stdout logging

import os, sys, logging, glob, zipfile, shutil

log = logging.getLogger()
log.setLevel( 10 )
log.addHandler( logging.StreamHandler( sys.stdout ) )

# Fake pkg_resources

import re

macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
solarisVersionString = re.compile(r"solaris-(\d)\.(\d+)-(.*)")

def compatible_platforms(provided,required):
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided==required:
        return True     # easy case

    # Mac OS X special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macosx designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = "%s.%s" % (reqMac.group(1), reqMac.group(2))
                if dversion == 7 and macosversion >= "10.3" or \
                    dversion == 8 and macosversion >= "10.4":

                    #import warnings
                    #warnings.warn("Mac eggs should be rebuilt to "
                    #    "use the macosx designation instead of darwin.",
                    #    category=DeprecationWarning)
                    return True
            return False    # egg isn't macosx or legacy darwin

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or \
            provMac.group(3) != reqMac.group(3):
            return False



        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # Solaris' special cases
    reqSol = solarisVersionString.match(required)
    if reqSol:
        provSol = solarisVersionString.match(provided)
        if not provSol:
            return False
        if provSol.group(1) != reqSol.group(1) or \
            provSol.group(3) != reqSol.group(3):
            return False
        if int(provSol.group(2)) > int(reqSol.group(2)):
            return False
        return True

    # XXX Linux and other platforms' special cases should go here
    return False

EGG_NAME = re.compile(
    r"(?P<name>[^-]+)"
    r"( -(?P<ver>[^-]+) (-py(?P<pyver>[^-]+) (-(?P<plat>.+))? )? )?",
    re.VERBOSE | re.IGNORECASE
).match

class Distribution( object ):
    def __init__( self, egg_name, project_name, version, py_version, platform ):
        self._egg_name = egg_name
        self.project_name = project_name
        if project_name is not None:
            self.project_name = project_name.replace( '-', '_' )
        self.version = version
        if version is not None:
            self.version = version.replace( '-', '_' )
        self.py_version = py_version
        self.platform = platform
        self.location = os.path.join( tmpd, egg_name ) + '.egg'
    def egg_name( self ):
        return self._egg_name
    @classmethod
    def from_filename( cls, basename ):
        project_name, version, py_version, platform = [None]*4
        basename, ext = os.path.splitext(basename)
        if ext.lower() == '.egg':
            match = EGG_NAME( basename )
            if match:
                project_name, version, py_version, platform = match.group( 'name','ver','pyver','plat' )
        return cls( basename, project_name, version, py_version, platform )

class pkg_resources( object ):
    pass

pkg_resources.Distribution = Distribution

# Fake galaxy.eggs

env = None
def get_env():
    return None

import urllib, urllib2, HTMLParser
class URLRetriever( urllib.FancyURLopener ):
    def http_error_default( *args ):
        urllib.URLopener.http_error_default( *args )

class Egg( object ):
    def __init__( self, distribution ):
        self.url = url + '/' + distribution.project_name.replace( '-', '_' )
        self.dir = tmpd
        self.distribution = distribution
    def set_distribution( self ):
        pass
    def unpack_if_needed( self ):
        pass
    def remove_doppelgangers( self ):
        pass
    def fetch( self, requirement ):
        """
        fetch() serves as the install method to pkg_resources.working_set.resolve()
        """
        def find_alternative():
            """
            Some platforms (e.g. Solaris) support eggs compiled on older platforms
            """
            class LinkParser( HTMLParser.HTMLParser ):
                """
                Finds links in what should be an Apache-style directory index
                """
                def __init__( self ):
                    HTMLParser.HTMLParser.__init__( self )
                    self.links = []
                def handle_starttag( self, tag, attrs ):
                    if tag == 'a' and 'href' in dict( attrs ):
                        self.links.append( dict( attrs )['href'] )
            parser = LinkParser()
            try:
                parser.feed( urllib2.urlopen( self.url + '/' ).read() )
            except urllib2.HTTPError, e:
                if e.code == 404:
                    return None
            parser.close()
            for link in parser.links:
                file = urllib.unquote( link ).rsplit( '/', 1 )[-1]
                tmp_dist = pkg_resources.Distribution.from_filename( file )
                if tmp_dist.platform is not None and \
                        self.distribution.project_name == tmp_dist.project_name and \
                        self.distribution.version == tmp_dist.version and \
                        self.distribution.py_version == tmp_dist.py_version and \
                        compatible_platforms( tmp_dist.platform, self.distribution.platform ):
                    return file
            return None
        if self.url is None:
            return None
        alternative = None
        try:
            url = self.url + '/' + self.distribution.egg_name() + '.egg'
            URLRetriever().retrieve( url, self.distribution.location )
            log.debug( "Fetched %s" % url )
        except IOError, e:
            if e[1] == 404 and self.distribution.platform != py:
                alternative = find_alternative()
                if alternative is None:
                    return None
            else:
                return None
        if alternative is not None:
            try:
                url = '/'.join( ( self.url, alternative ) )
                URLRetriever().retrieve( url, os.path.join( self.dir, alternative ) )
                log.debug( "Fetched %s" % url )
            except IOError, e:
                return None
            self.platform = alternative.split( '-', 2 )[-1].rsplit( '.egg', 1 )[0]
            self.set_distribution()
        self.unpack_if_needed()
        self.remove_doppelgangers()
        global env
        env = get_env() # reset the global Environment object now that we've obtained a new egg
        return self.distribution

def create_zip():
    fname = 'galaxy_eggs-%s.zip' % platform
    z = zipfile.ZipFile( fname, 'w', zipfile.ZIP_STORED )
    for egg in glob.glob( os.path.join( tmpd, '*.egg' ) ):
        z.write( egg, 'eggs/' + os.path.basename( egg ) )
    z.close()
    print 'Egg package is in %s' % fname
    print "To install the eggs, please copy this file to your Galaxy installation's root"
    print "directory and unpack with:"
    print "  unzip %s" % fname

def clean():
    shutil.rmtree( tmpd )

import tempfile
tmpd = tempfile.mkdtemp()

failures = []

# Automatically generated egg definitions follow

py = 'py2.7'
url = 'http://eggs.galaxyproject.org'
platform = 'py2.7-linux-x86_64-ucs2'
dists = [
          Distribution( 'Mako-0.4.1-py2.7', 'Mako', '0.4.1', '2.7', 'None' ),
          Distribution( 'importlib-1.0.3-py2.7', 'importlib', '1.0.3', '2.7', 'None' ),
          Distribution( 'pysam-0.4.2_kanwei_b10f6e722e9a-py2.7-linux-x86_64-ucs2', 'pysam', '0.4.2-kanwei-b10f6e722e9a', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'ordereddict-1.1-py2.7', 'ordereddict', '1.1', '2.7', 'None' ),
          Distribution( 'Fabric-1.7.0-py2.7', 'Fabric', '1.7.0', '2.7', 'None' ),
          Distribution( 'Babel-1.3-py2.7', 'Babel', '1.3', '2.7', 'None' ),
          Distribution( 'Whoosh-0.3.18-py2.7', 'Whoosh', '0.3.18', '2.7', 'None' ),
          Distribution( 'Parsley-1.1-py2.7', 'Parsley', '1.1', '2.7', 'None' ),
          Distribution( 'Cheetah-2.2.2-py2.7-linux-x86_64-ucs2', 'Cheetah', '2.2.2', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'guppy-0.1.10-py2.7-linux-x86_64-ucs2', 'guppy', '0.1.10', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'PyRods-3.2.4-py2.7-linux-x86_64-ucs2', 'PyRods', '3.2.4', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'paramiko-1.11.1-py2.7', 'paramiko', '1.11.1', '2.7', 'None' ),
          Distribution( 'lrucache-0.2-py2.7', 'lrucache', '0.2', '2.7', 'None' ),
          Distribution( 'sqlalchemy_migrate-0.7.2-py2.7', 'sqlalchemy-migrate', '0.7.2', '2.7', 'None' ),
          Distribution( 'NoseHTML-0.4.1-py2.7', 'NoseHTML', '0.4.1', '2.7', 'None' ),
          Distribution( 'pexpect-2.4-py2.7', 'pexpect', '2.4', '2.7', 'None' ),
          Distribution( 'amqp-1.4.3-py2.7', 'amqp', '1.4.3', '2.7', 'None' ),
          Distribution( 'drmaa-0.6-py2.7', 'drmaa', '0.6', '2.7', 'None' ),
          Distribution( 'psycopg2-2.5.1_9.2.4_static-py2.7-linux-x86_64-ucs2', 'psycopg2', '2.5.1-9.2.4-static', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'bx_python-0.7.2-py2.7-linux-x86_64-ucs2', 'bx-python', '0.7.2', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'PasteDeploy-1.5.0-py2.7', 'PasteDeploy', '1.5.0', '2.7', 'None' ),
          Distribution( 'WebHelpers-1.3-py2.7', 'WebHelpers', '1.3', '2.7', 'None' ),
          Distribution( 'bioblend-0.4.2-py2.7', 'bioblend', '0.4.2', '2.7', 'None' ),
          Distribution( 'docutils-0.7-py2.7', 'docutils', '0.7', '2.7', 'None' ),
          Distribution( 'kombu-3.0.12-py2.7', 'kombu', '3.0.12', '2.7', 'None' ),
          Distribution( 'numpy-1.6.0-py2.7-linux-x86_64-ucs2', 'numpy', '1.6.0', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'pysqlite-2.5.6_3.6.17_static-py2.7-linux-x86_64-ucs2', 'pysqlite', '2.5.6-3.6.17-static', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'mock-1.0.1-py2.7', 'mock', '1.0.1', '2.7', 'None' ),
          Distribution( 'raven-3.1.8-py2.7', 'raven', '3.1.8', '2.7', 'None' ),
          Distribution( 'Beaker-1.4-py2.7', 'Beaker', '1.4', '2.7', 'None' ),
          Distribution( 'PyYAML-3.10-py2.7-linux-x86_64-ucs2', 'PyYAML', '3.10', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'SQLAlchemy-0.7.9-py2.7-linux-x86_64-ucs2', 'SQLAlchemy', '0.7.9', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'simplejson-2.1.1-py2.7', 'simplejson', '2.1.1', '2.7', 'None' ),
          Distribution( 'NoseTestDiff-0.1-py2.7', 'NoseTestDiff', '0.1', '2.7', 'None' ),
          Distribution( 'poster-0.8.1-py2.7', 'poster', '0.8.1', '2.7', 'None' ),
          Distribution( 'python_lzo-1.08_2.03_static-py2.7-linux-x86_64-ucs2', 'python-lzo', '1.08-2.03-static', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'wchartype-0.1-py2.7', 'wchartype', '0.1', '2.7', 'None' ),
          Distribution( 'Tempita-0.5.1-py2.7', 'Tempita', '0.5.1', '2.7', 'None' ),
          Distribution( 'MarkupSafe-0.12-py2.7-linux-x86_64-ucs2', 'MarkupSafe', '0.12', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'MySQL_python-1.2.3c1_5.1.41_static-py2.7-linux-x86_64-ucs2', 'MySQL-python', '1.2.3c1-5.1.41-static', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'ssh-1.7.14-py2.7', 'ssh', '1.7.14', '2.7', 'None' ),
          Distribution( 'Routes-1.12.3-py2.7', 'Routes', '1.12.3', '2.7', 'None' ),
          Distribution( 'elementtree-1.2.6_20050316-py2.7', 'elementtree', '1.2.6-20050316', '2.7', 'None' ),
          Distribution( 'decorator-3.1.2-py2.7', 'decorator', '3.1.2', '2.7', 'None' ),
          Distribution( 'GeneTrack-2.0.0_beta_1_dev_48da9e998f0caf01c5be731e926f4b0481f658f0-py2.7', 'GeneTrack', '2.0.0-beta-1-dev-48da9e998f0caf01c5be731e926f4b0481f658f0', '2.7', 'None' ),
          Distribution( 'WebOb-0.8.5-py2.7', 'WebOb', '0.8.5', '2.7', 'None' ),
          Distribution( 'threadframe-0.2-py2.7-linux-x86_64-ucs2', 'threadframe', '0.2', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'pycrypto-2.5-py2.7-linux-x86_64-ucs2', 'pycrypto', '2.5', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'boto-2.27.0-py2.7', 'boto', '2.27.0', '2.7', 'None' ),
          Distribution( 'Paste-1.7.5.1-py2.7', 'Paste', '1.7.5.1', '2.7', 'None' ),
          Distribution( 'python_daemon-1.5.5-py2.7', 'python-daemon', '1.5.5', '2.7', 'None' ),
          Distribution( 'mercurial-2.2.3-py2.7-linux-x86_64-ucs2', 'mercurial', '2.2.3', '2.7', 'linux-x86_64-ucs2' ),
          Distribution( 'wsgiref-0.1.2-py2.7', 'wsgiref', '0.1.2', '2.7', 'None' ),
          Distribution( 'SVGFig-1.1.6-py2.7', 'SVGFig', '1.1.6', '2.7', 'None' ),
          Distribution( 'pytz-2013.9-py2.7', 'pytz', '2013.9', '2.7', 'None' ),
          Distribution( 'nose-0.11.1-py2.7', 'nose', '0.11.1', '2.7', 'None' ),
          Distribution( 'python_openid-2.2.5-py2.7', 'python-openid', '2.2.5', '2.7', 'None' ),
          Distribution( 'requests-2.2.1-py2.7', 'requests', '2.2.1', '2.7', 'None' ),
          Distribution( 'anyjson-0.3.3-py2.7', 'anyjson', '0.3.3', '2.7', 'None' ),
          Distribution( 'WebError-0.8a-py2.7', 'WebError', '0.8a', '2.7', 'None' ),
          Distribution( 'twill-0.9-py2.7', 'twill', '0.9', '2.7', 'None' ),
]

for d in dists:
    e = Egg( d )
    if not e.fetch( None ):
        failures.append( e )

if failures:
    print ""
    print "Failed:"
    for e in failures:
        print e.distribution.project_name
else:
    create_zip()
clean()
