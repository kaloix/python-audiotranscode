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

# Arguments
parser = argparse.ArgumentParser(
		description='Converts audo files to the desired format preserving the directory structure',
		epilog='Copyright © 2015 Stefan Schindler. Licensed under the GNU General Public License Version 3.')
parser.add_argument('input', help='Source path or file', metavar='<source>')
parser.add_argument('output', help='Output path or file', metavar='<target>')
parser.add_argument('-f', '--format', help='Target audio format in form of filename extension, required when converting directories', metavar='<format>')
parser.add_argument('-b', '--bitrate', type=int, help='Target audio bitrate in kbps', metavar='<kbps>')
parser.add_argument('-s', '--skip', action='store_true', help='Skip file(s) when already present at target, does not check target file contents in any way')
parser.add_argument('-d', '--delete', action='store_true', help='Delete file(s) in target directory when there is no equivalent in the source directory') # TODO
parser.add_argument('-c', '--codecs', action='store_true', help='List all available encoders and decoders on the command line')
args = parser.parse_args()

# List available codecs
transcoder = audiotranscode.AudioTranscode()
if args.codecs:
	row_format = "{:>10}" * 3
	print('Encoders:')
	print(row_format.format('ENCODER', 'INSTALLED', 'FILETYPE'))
	for enc in transcoder.Encoders:
		avail = 'yes' if enc.available() else 'no'
		print(row_format.format(enc.command[0], avail, enc.filetype))

	print('Decoders:')
	print(row_format.format('ENCODER', 'INSTALLED', 'FILETYPE'))
	for dec in transcode.Decoders:
		avail = 'yes' if dec.available() else 'no'
		print(row_format.format(dec.command[0], avail, dec.filetype))
	raise SystemExit

# Convert single file
if not os.path.exists(args.input):
	parser.error('Source does not exist')
if os.path.isfile(args.input):
	if args.skip and os.path.isfile(args.output):
		print('Target file already exists, nothing to do')
		raise SystemExit

	print('Converting {} ...'.format(args.input), end=' ', flush=True)
	try:
		transcoder.transcode(args.input, args.output, args.bitrate)
	except (audiotranscode.TranscodeError, IOError) as err:
		if os.path.exists(args.output):
			os.remove(args.output)
		print(red(str(err)))
	except KeyboardInterrupt:
		if os.path.exists(args.output):
			os.remove(args.output)
		print(red('Canceled'))
	else:
		print(green('OK'))
	raise SystemExit

# Validate source and target as directories
if not os.path.isdir(args.input):
	parser.error('Source is invalid')
if not os.path.exists(args.output):
	parser.error('Target directory does not exist')
if args.format is None:
	parser.error('Specify target format when converting directories')

# Check target format
valid_format = False
for enc in transcoder.Encoders:
	valid_format |= enc.filetype == args.format
if not valid_format:
	parser.error('{} is not a valid target format'.format(args.format))

# Containers and counters
skip_format = ['jpg', 'png', 'pdf', 'txt', 'md']
file_transcodings = list()
skipped_format = 0
skipped_present = 0

# Search input directory
for (current_indir, dirnames, filenames) in os.walk(args.input):
	# Prepare output directory
	current_outdir = os.path.join(args.output, os.path.relpath(current_indir, args.input))
	try:
		os.makedirs(os.path.abspath(current_outdir))
	except FileExistsError:
		pass
	
	# Handle files in current directory
	for name in filenames:
		# Calculate filename properties
		infile = os.path.join(current_indir, name)
		extension = name.split('.')[-1]
		outfile = os.path.join(current_outdir, name.rstrip(extension) + args.format)
		
		# Skip known others
		if args.skip and extension in skip_format:
			print('Skipping non-audio: {}'.format(infile))
			skipped_format += 1
			continue
		
		# Skip ones that are present in target directory
		if os.path.exists(outfile):
			skipped_present += 1
			continue
		
		# Store as dict instead of tuple to prevent future faulty file deletions
		file_transcodings.append({'in': infile, 'ext': extension, 'out': outfile})
			
# Ask user to continue
print('{} files to convert, skipped {} already present in output, skipped {} non-audio files'.format(len(file_transcodings), skipped_present, skipped_format))
user_continue = input('Continue? [y/n] ')
if not user_continue == 'y':
	print(red('Canceled'))
	raise SystemExit

# Error counter
error_count = dict()
def count_error(extension):
	if extension in error_count:
		error_count[extension] += 1
	else:
		error_count[extension] = 1
		
# Transcode files with audiotranscode by Tom Wallroth under GPLv3
for file in file_transcodings:
	print('Converting {} ...'.format(file['in']), end=' ', flush=True)
	try:
		transcoder.transcode(file['in'], file['out'], args.bitrate)
	except (audiotranscode.TranscodeError, IOError) as err:
		if os.path.exists(file['out']):
			os.remove(file['out'])
		count_error(file['ext'])
		print(red(str(err).strip('\'')))
	except KeyboardInterrupt:
		if os.path.exists(file['out']):
			os.remove(file['out'])
		print(red('Canceled'))
		break
	else:
		print(green('OK'))

# Error statistic
stat_string = list()
for extension in error_count:
	stat_string.append('{}x .{}'.format(error_count[extension], extension))
if len(error_count) > 0:
	print(red('Faild to transcode: {}'.format(', '.join(stat_string))))

