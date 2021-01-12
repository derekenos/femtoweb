
from unittest import TestCase

from femtoweb import server
from femtoweb.server import (
    CouldNotParse,
    as_choice,
    as_nonempty,
    as_type,
    get_file_path_content_type,
    maybe_as,
    with_default_as,
)


class Tester(TestCase):
    def test_as_type_int(self):
        as_int = as_type(int)
        for a, b in (
                (None, CouldNotParse),
                ('', CouldNotParse),
                ('0', 0),
                ('1', 1),
                ('-1', -1),
                ('1.1', CouldNotParse),
                ('a', CouldNotParse),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, as_int, a)
            else:
                self.assertEqual(as_int(a), b)


    def test_as_type_float(self):
        as_int = as_type(float)
        for a, b in (
                (None, CouldNotParse),
                ('', CouldNotParse),
                ('0', 0.0),
                ('1', 1.0),
                ('-1', -1.0),
                ('1.1', 1.1),
                ('a', CouldNotParse),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, as_int, a)
            else:
                self.assertEqual(as_int(a), b)


    def test_as_choice(self):
        parser = as_choice('yes', 'no')
        for a, b in (
                (None, CouldNotParse),
                ('', CouldNotParse),
                ('0', CouldNotParse),
                ('1', CouldNotParse),
                ('-1', CouldNotParse),
                ('1.1', CouldNotParse),
                ('a', CouldNotParse),
                ('yes', 'yes'),
                ('no', 'no'),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, parser, a)
            else:
                self.assertEqual(parser(a), b)


    def test_maybe_as(self):
        parser = maybe_as(as_type(int))
        for a, b in (
                (None, None),
                ('', CouldNotParse),
                ('0', 0),
                ('1', 1),
                ('-1', -1),
                ('1.1', CouldNotParse),
                ('a', CouldNotParse),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, parser, a)
            else:
                self.assertEqual(parser(a), b)


    def test_as_nonempty(self):
        parser = as_nonempty(as_type(str))
        for a, b in (
                (None, CouldNotParse),
                ('', CouldNotParse),
                ('0', '0'),
                ('1', '1'),
                ('-1', '-1'),
                ('1.1', '1.1'),
                ('a', 'a'),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, parser, a)
            else:
                self.assertEqual(parser(a), b)


    def test_with_default_as(self):
        parser = with_default_as(as_type(int), 0)
        for a, b in (
                (None, 0),
                ('', 0),
                ('0', 0),
                ('1', 1),
                ('-1', -1),
                ('1.1', 0),
                ('a', 0),
            ):
            if b is CouldNotParse:
                self.assertRaises(CouldNotParse, parser, a)
            else:
                self.assertEqual(parser(a), b)


    def test_get_file_path_content_type(self):
        for a, b in (
                ('', server.APPLICATION_OCTET_STREAM),
                ('test', server.APPLICATION_OCTET_STREAM),
                ('test.unsupported', server.APPLICATION_OCTET_STREAM),
                ('test.js', server.APPLICATION_JAVASCRIPT),
                ('test.schema.json', server.APPLICATION_SCHEMA_JSON),
                ('test.json', server.APPLICATION_JSON),
                ('test.gif', server.IMAGE_GIF),
                ('test.jpeg', server.IMAGE_JPEG),
                ('test.jpg', server.IMAGE_JPEG),
                ('test.png', server.IMAGE_PNG),
                ('test.html', server.TEXT_HTML),
                ('test.py', server.APPLICATION_PYTHON),
                ('test.txt', server.TEXT_PLAIN),
            ):
            self.assertEqual(get_file_path_content_type(a), b)
