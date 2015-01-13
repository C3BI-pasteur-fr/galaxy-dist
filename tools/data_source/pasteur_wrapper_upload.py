#!/usr/bin/env python
#Processes uploads from the user.

# WARNING: Changes in this tool (particularly as related to parsing) may need
# to be reflected in galaxy.web.controllers.tool_runner and galaxy.tools

import sys, os
import subprocess
from galaxy import eggs
# need to import model before sniff to resolve a circular import dependency
import galaxy.model
from galaxy.datatypes.registry import Registry
from galaxy import util
from galaxy.util.json import *


def safe_dict(d):
    """
    Recursively clone json structure with UTF-8 dictionary keys
    http://mellowmachines.com/blog/2009/06/exploding-dictionary-with-unicode-keys-as-python-arguments/
    """
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v)) for k,v in d.iteritems()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d

def parse_outputs( args ):
    rval = {}
    for arg in args:
        id, files_path, path = arg.split( ':', 2 )
        rval[int( id )] = ( path, files_path )
    return rval

def __main__():

    if len( sys.argv ) < 4:
        print >>sys.stderr, 'usage: upload.py <root> <datatypes_conf> <json paramfile> <output spec> ...'
        sys.exit( 1 )

    output_paths = parse_outputs( sys.argv[4:] )
    json_file = open( 'galaxy.json', 'w' )

    registry = Registry()
    registry.load_datatypes( root_dir=sys.argv[1], config=sys.argv[2] )
    qsub_flag = 0
    num_lines = 0
    #outup = open("/pasteur/projets/common/galaxy/upload.output","w")
    for line in open( sys.argv[3], 'r' ):
        num_lines += 1
        dataset = from_json_string( line )
        dataset = util.bunch.Bunch( **safe_dict( dataset ) )
        #outup.write("%s\n" % (dataset))
        if dataset.type == 'server_dir':
            qsub_flag += 1
    dir_python = os.path.dirname(sys.argv[0])
    if num_lines == qsub_flag:
        command = "qrsh -q galaxy -V -now n python %s %s" % (os.path.join(dir_python, 'upload.py'), ' '.join(sys.argv[1:]))
        print >>sys.stdout, 'cluster executing of : %s' % command
    else:
        command = "python %s %s" % (os.path.join(dir_python, 'upload.py'), ' '.join(sys.argv[1:]))
        print >>sys.stdout, 'local executing of : %s' % command
    #outup.write("%s\n" % command)
    try:
        proc = subprocess.Popen( args = command, stderr = subprocess.STDOUT, stdout = subprocess.PIPE,
                                shell = True, env = os.environ, close_fds = True )
        #proc = subprocess.Popen( args = command, stderr = outup, stdout = outup,
        #                        shell = True, env = os.environ, close_fds = True )
        proc.wait()
        #outup.close()
    except Exception:
        print >>sys.stderr, 'Error with the command : %s' % command
        #outup.close()
        sys.exit( 1 )

if __name__ == '__main__':
    __main__()
