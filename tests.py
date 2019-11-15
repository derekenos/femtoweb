
from unittest import TestCase

from .server import (
    CouldNotParse,
    as_type,
    as_choice,
    as_maybe,
    as_nonempty,
    as_with_default,
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


    def test_as_maybe(self):
        parser = as_maybe(as_type(int))
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


    def test_as_with_default(self):
        parser = as_with_default(as_type(int), 0)
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
