#!/usr/bin/env python3

# Imports
import os
import argparse
import audiotranscode

# Colors
RED = '\033[31m'
GREEN = '\033[32m'
ENDC = '\033[0m'
def red(msg):
	return(''.join([RED, msg, ENDC]))
def green(msg):
	return(''.join([GREEN, msg, ENDC]))

# Arguments
parser = argparse.ArgumentParser(
		description='Converts audo files to the desired format preserving the directory structure',
		epilog='Copyright © 2015 Stefan Schindler. Licensed under the GNU General Public License Version 3.')
parser.add_argument('input', help='Source path or file', metavar='<source>')
parser.add_argument('output', help='Output path or file, must be of same type as source', metavar='<target>')
parser.add_argument('-c', '--codecs', action='store_true', help='List all available encoders and decoders on the command line')
parser.add_argument('-b', '--bitrate', type=int, help='Target audio bitrate in kbps', metavar='<kbps>')
parser.add_argument('-f', '--format', help='Target audio format in form of filename extension, required when converting directories', metavar='<format>')
parser.add_argument('-s', '--skip', action='store_true', help='Skip file(s) when already present at target, does not check target file contents in any way')
parser.add_argument('-d', '--delete', action='store_true', help='Delete files and folders in target directory when there is no equivalent in the source directory')
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
	print(row_format.format('DECODER', 'INSTALLED', 'FILETYPE'))
	for dec in transcoder.Decoders:
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
		if os.path.isfile(args.output):
			os.remove(args.output)
		print(red(str(err)))
		print('Try the --codecs switch to see all installed codecs')
	except KeyboardInterrupt:
		if os.path.isfile(args.output):
			os.remove(args.output)
		print(red('Canceled'))
	else:
		print(green('OK'))
	raise SystemExit

# Convert directory, validate source and target
if not os.path.isdir(args.input):
	parser.error('Source is invalid')
if not os.path.isdir(args.output):
	parser.error('Target directory does not exist')
if args.format is None:
	parser.error('Specify --format of target when converting directories')

# Validate target format
valid_format = False
for enc in transcoder.Encoders:
	valid_format |= enc.filetype == args.format
if not valid_format:
	parser.error('{} is not a valid target format'.format(args.format))

# Containers and counters
file_transcodings = list()
valid_outfiles = list()
skipped = 0

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
		valid_outfiles.append(os.path.abspath(outfile))

		# Skip ones that are present in target directory
		if args.skip and os.path.exists(outfile):
			skipped += 1
			continue

		# Store as dict instead of tuple to prevent future faulty file deletions
		file_transcodings.append({'in': infile, 'ext': extension, 'out': outfile})

# Ask user to continue
print('{} files to convert, skipped {} already present in target directory'.format(len(file_transcodings), skipped))
def ask_continue():
	try:
		user_continue = input('Continue? [y/n] ')
	except KeyboardInterrupt:
		print(red('Canceled'))
		raise SystemExit
	if user_continue != 'y':
		print(red('Canceled'))
		raise SystemExit
if file_transcodings:
	ask_continue()
elif not args.delete:
	print('Nothing to do')
	raise SystemExit

# Transcode files recursively
error_count = dict()
success_count = 0
total_count = 0
for file in file_transcodings:
	print('[{}/{}] Converting {} ...'.format(total_count+1, len(file_transcodings), file['in']), end=' ', flush=True)
	try:
		transcoder.transcode(file['in'], file['out'], args.bitrate)
	except (audiotranscode.TranscodeError, IOError) as err:
		if os.path.isfile(file['out']):
			os.remove(file['out'])
		if file['ext'] in error_count:
			error_count[file['ext']] += 1
		else:
			error_count[file['ext']] = 1
		print(red(str(err).strip('\'')))
	except KeyboardInterrupt:
		if os.path.isfile(file['out']):
			os.remove(file['out'])
		print(red('Canceled'))
		break
	else:
		success_count += 1
		print(green('OK'))
	total_count += 1

# Transcode statistics
if success_count > 0:
	print(green('Sucessfully transcoded {} files'.format(success_count)))
stat_string = list()
for extension in error_count:
	stat_string.append('{}x .{}'.format(error_count[extension], extension))
if len(error_count) > 0:
	print(red('Faild to transcode: {}'.format(', '.join(stat_string))))
	print('Try the --codecs switch to see all installed codecs')

# Find invalid target files
if not args.delete:
	raise SystemExit
invalid_outfiles = list()
for (dirpath, dirnames, filenames) in os.walk(args.output):
	for name in filenames:
		filepath = os.path.join(dirpath, name)
		if not os.path.abspath(filepath) in valid_outfiles:
			print('Will delete: {}'.format(filepath))
			invalid_outfiles.append(filepath)

# Ask user for confirmation
print('Will delete {} invalid files in target directory'.format(len(invalid_outfiles)))
if len(invalid_outfiles) > 0:
	ask_continue()
	for entry in invalid_outfiles:
		os.remove(entry)

# Delete empty directories
for (dirpath, dirnames, filenames) in os.walk(args.output, topdown=False):
	try:
		os.rmdir(dirpath)
	except OSError:
		pass
	else:
		print('Deleted empty directory: {}'.format(dirpath))
print(green('Finished'))

