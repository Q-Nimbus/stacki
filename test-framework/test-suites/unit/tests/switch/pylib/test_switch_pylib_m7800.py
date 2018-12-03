import pytest
from unittest.mock import patch
from unittest.mock import ANY

import json

from stack.switch.m7800 import SwitchMellanoxM7800
from stack.switch import SwitchException

INPUT_DATA = [
	['m7800_parse_partitions_input.txt', 'm7800_parse_partitions_output.json'],
	['m7800_parse_partitions_with_member_named_all_input.txt', 'm7800_parse_partitions_with_member_named_all_output.json'],
]

@patch('stack.switch.m7800.ExpectMore', autospec = True)
class TestSwitchMellanoxM7800:

	@pytest.mark.parametrize('input_file,output_file', INPUT_DATA)
	def test_partitions_can_parse_guid_members(self, mock_expectmore, input_file, output_file):
		dirn = '/export/test-files/switch/'
		expected_output = json.load(open(dirn + output_file))
		with open(dirn + input_file) as test_file:
			input_data = test_file.read().splitlines()

		mock_expectmore.return_value.isalive.return_value = True
		mock_expectmore.return_value.ask.return_value = input_data

		s = SwitchMellanoxM7800('fakeip')
		assert(s.partitions == expected_output)

	def test_reload(self, mock_expectmore):
		"""Expect this to end the conversation and request a reload."""
		test_switch = SwitchMellanoxM7800('fakeip')
		test_switch.reload()
		mock_expectmore.return_value.end.assert_called_with('reload noconfirm')

	def test_image_boot_next(self, mock_expectmore):
		"""Expect this to set the next image to boot as the new image."""
		test_switch = SwitchMellanoxM7800('fakeip')
		test_switch.image_boot_next()
		mock_expectmore.return_value.say.assert_called_with('image boot next')

	def test_install_firmware(self, mock_expectmore):
		"""Expect this to try to install the user requested firmware."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_name = 'my_amazing_firmware'
		test_switch.install_firmware(image = firmware_name)
		mock_expectmore.return_value.ask.assert_called_with(
			f'image install {firmware_name}',
			timeout=ANY
		)

	def test_image_delete(self, mock_expectmore):
		"""Expect this to try to delete the user requested firmware."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_name = 'my_amazing_firmware'
		test_switch.image_delete(image = firmware_name)
		mock_expectmore.return_value.ask.assert_called_with(f'image delete {firmware_name}')

	def test_image_delete_error(self, mock_expectmore):
		"""Expect this to raise an error if there is an error response."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_name = 'my_amazing_firmware'
		error_message = '% file not found'
		mock_expectmore.return_value.ask.return_value = [error_message]

		with pytest.raises(SwitchException) as exception:
			test_switch.image_delete(image = firmware_name)
		assert(error_message in str(exception))

	@pytest.mark.parametrize('protocol', SwitchMellanoxM7800.SUPPORTED_IMAGE_FETCH_PROTOCOLS)
	def test_image_fetch(self, mock_expectmore, protocol):
		"""Expect this to try to fetch the user requested firmware."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_url = f'{protocol}://sometrustworthysite.ru'
		# add success condition return value
		mock_expectmore.return_value.ask.return_value = ['100.0%']
		test_switch.image_fetch(url = firmware_url)
		mock_expectmore.return_value.ask.assert_called_with(
			f'image fetch {firmware_url}',
			timeout=ANY
		)

	def test_image_fetch_bad_protocol(self, mock_expectmore):
		"""Expect an error to be raised on an unsupported protocol."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_url = 'git://user@sometrusworthysite.ru/sometrustworthyrepo.git'
		# add success condition return value to ensure the exception is because of the
		# unsupported protocol.
		mock_expectmore.return_value.ask.return_value = ['100.0%']

		with pytest.raises(SwitchException):
			test_switch.image_fetch(url = firmware_url)

	def test_image_fetch_error_with_message(self, mock_expectmore):
		"""Expect an error to be raised due to a missing success indicator and the error message to be captured."""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_url = f'{test_switch.SUPPORTED_IMAGE_FETCH_PROTOCOLS[0]}://sometrustworthysite.ru'

		error_message = '% unauthorized'
		mock_expectmore.return_value.ask.return_value = ['other junk', error_message,]
		with pytest.raises(SwitchException) as exception:
			test_switch.image_fetch(url = firmware_url)
		assert(error_message in str(exception))

	def test_image_fetch_error_without_message(self, mock_expectmore):
		"""Expect an error to be raised due to a missing success indicator.

		The error message is not captured because it is missing the beggining % symbol.
		"""
		test_switch = SwitchMellanoxM7800('fakeip')
		firmware_url = f'{test_switch.SUPPORTED_IMAGE_FETCH_PROTOCOLS[0]}://sometrustworthysite.ru'

		irrelevant_output = ['other junk', 'irrelevant',]
		mock_expectmore.return_value.ask.return_value = irrelevant_output
		with pytest.raises(SwitchException) as exception:
			test_switch.image_fetch(url = firmware_url)
		assert(not any((output in str(exception) for output in irrelevant_output)))

	def test_show_images(self, mock_expectmore):
		"""Expect this to try to list the current and available firmware images."""
		test_switch = SwitchMellanoxM7800('fakeip')
		test_switch.show_images()
		mock_expectmore.return_value.ask.assert_called_with('show images')

	def test_show_images_no_data(self, mock_expectmore):
		"""Test that default data is returned when nothing is returned from the switch."""
		expected_data = {
			'installed_images': [],
			'last_boot_partition': None,
			'next_boot_partition': None,
			'images_fetched_and_available': [],
		}
		mock_expectmore.return_value.ask.return_value = []
		test_switch = SwitchMellanoxM7800('fakeip')
		assert(test_switch.show_images() == expected_data)

	def test_show_images_kitchen_sink(self, mock_expectmore):
		"""Test that all information is parsed when present."""
		with open('/export/test-files/switch/m7800_show_images_console.txt') as test_file:
			test_console_response = test_file.read().splitlines()

		expected_data = {
			'installed_images': [
				{'Partition 1': 'X86_64 3.6.4006 2017-07-03 16:17:39 x86_64'},
				{'Partition 2': 'X86_64 3.6.4006 2017-07-03 16:17:39 x86_64'},
			],
			'last_boot_partition': 1,
			'next_boot_partition': 1,
			# show_images() currently only captures the filename and skips the version
			# information that follows it. I want this to break if/when that behavior is fixed.
			'images_fetched_and_available': [
				'image-X86_64-3.6.2002.img',
				'image-X86_64-3.6.3004.img',
				'image-X86_64-3.6.4006.img',
				'image-X86_64-3.6.5009.img',
				'image-X86_64-3.6.8010.img',
			],
		}
		mock_expectmore.return_value.ask.return_value = test_console_response
		test_switch = SwitchMellanoxM7800('fakeip')
		assert(test_switch.show_images() == expected_data)

	def test__get_errors(self, mock_expectmore):
		"""Confirm that strings starting with '%' are treated as errors."""
		command_response = ['foobar%%%%%%', 'f%o%b%a%r%', '%foobar%', '%errors!']
		test_switch = SwitchMellanoxM7800('fakeip')
		expected = sorted(['%foobar%', '%errors!'])
		assert(sorted(test_switch._get_errors(command_response)) == expected)
