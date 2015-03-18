#!/usr/bin/env python3

# Imports
import os
import argparse
import audiotranscode

# Colors
YELLOW = '\033[33m'
RED = '\033[31m'
GREEN = '\033[32m'
ENDC = '\033[0m'
def yellow(msg):
	return(''.join([YELLOW, msg, ENDC]))
def red(msg):
	return(''.join([RED, msg, ENDC]))
def green(msg):
	return(''.join([GREEN, msg, ENDC]))

# Conversion settings
format_bitrate = dict()
format_bitrate['ogg'] = 64

# Arguments
parser = argparse.ArgumentParser(
		description='Converts audo files to the desired format preserving the directory structure',
		epilog='Copyright © 2015 Stefan Schindler. Licensed under the GNU General Public License Version 3.')
parser.add_argument('indir', help='Source path', metavar='<source>')
parser.add_argument('outdir', help='Output path', metavar='<target>')
parser.add_argument('-f', '--format', default='ogg', choices=format_bitrate, help='Target audio format in form of filename extension', metavar='<format>')
args = parser.parse_args()
if not os.path.exists(args.indir):
	parser.error('Source directory does not exist.')
if not os.path.exists(args.outdir):
	parser.error('Target directory does not exist.')
	
# Containers
input_format = {'mp3', 'flac', 'ogg', 'opus'}
skip_format = {'jpg', 'png', 'pdf', 'txt', 'md'}
process_files = list()
skip_count = unknown_count = present_count = 0

# Search input directory
for (curindir, dirnames, filenames) in os.walk(args.indir):
	# Calculate directory paths
	reldir = os.path.relpath(curindir, args.indir)
	curoutdir = os.path.join(args.outdir, reldir)
	
	# Create all output directories
	try:
		os.makedirs(curoutdir)
	except FileExistsError:
		pass
	
	# Handle files in current directory
	for name in filenames:
		# Calculate file properties
		relfile = os.path.join(reldir, name)
		infile = os.path.join(curindir, name)
		extension = name.split('.')[-1]
		
		# Skip known others
		if extension in skip_format:
			print('Skipping non audio: {}'.format(relfile))
			skip_count += 1
			continue
		
		# Store audio files
		if extension in input_format:
			outname = name.rstrip(extension) + args.format
			outfile = os.path.join(curoutdir, outname)
			
			# Check target direcotry
			if os.path.exists(outfile):
				print('Already present: {}'.format(relfile))
				present_count += 1
			else:
				process_files.append((infile, outfile))
		
		# Skip unknown others
		else:
			print(yellow('Skipping unknown file: {}'.format(relfile)))
			unknown_count += 1
print('{} files to convert, skipped {} already present, skipped {} non-audio, skipped {} unknown file'.format(len(process_files), present_count, skip_count, unknown_count))

# Delete file if it's not contained by protected directory
def secure_remove(path, protect):
	if path.startswith(protect):
		print(red('Programming error: Prevented deletion of {}, {} is protected'.format(path, protect)))
	else:
		os.remove(path)
		
# Transcode files with audiotranscode by Tom Wallroth under GPLv3
TRANSCODER = audiotranscode.AudioTranscode()
BITRATE = format_bitrate[args.format]
for file in process_files:
	print('Converting {} ...'.format(file[0]), end=' ', flush=True)
	IN_FILE = file[0]
	OUT_FILE = file[1]
	try:
		TRANSCODER.transcode(IN_FILE, OUT_FILE, BITRATE)
	except (audiotranscode.TranscodeError, IOError, KeyboardInterrupt) as err:
		secure_remove(file[1], args.indir)
		print(red(str(err).strip('\'')))
		print(red('Process aborted'))
		raise SystemExit
	else:
		print(green('OK'))

