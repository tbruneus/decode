"""
Test cases for decode
"""

from unittest import TestCase

import decode


class TestDecode(TestCase):
    def test_get_dictionary(self):
        with self.subTest('Basic functionality'):
            dic = decode.get_dictionary('a/b\nc/d\ne/f', False)
            self.assertEquals(dic, {'a': 'b', 'c': 'd', 'e': 'f'}, 'Basic parsing not working.')
        with self.subTest('Comments'):
            dic = decode.get_dictionary('#comment\na/b #foo\nc/d\ne/f#bar', False)
            self.assertEquals(dic, {'a': 'b', 'c': 'd', 'e': 'f'}, 'Comments not handled correctly.')
        with self.subTest('Empty lines'):
            dic = decode.get_dictionary('\na/b\n\n\nc/d\ne/f\n\n', False)
            self.assertEquals(dic, {'a': 'b', 'c': 'd', 'e': 'f'}, 'Empty lines not handled correctly.')
        with self.subTest('Empty dictionary'):
            with self.assertRaises(ValueError, msg='Dictionary with no key-value pairs should raise a ValueError'):
                decode.get_dictionary('#a/b\ncccc\ne|f\ng:h', False)
        with self.subTest('Reverse'):
            dic = decode.get_dictionary('a/b\nc/d\ne/f', True)
            self.assertEquals(dic, {'b': 'a', 'd': 'c', 'f': 'e'}, 'Dictionary reverse not working.')
        with self.subTest('String strip'):
            dic = decode.get_dictionary(' a/b  \nc /d\ne  /  f\t', False)
            self.assertEquals(dic, {'a': 'b', 'c': 'd', 'e': 'f'}, 'String stripping not working.')
        with self.subTest('Unescaped unicode'):
            dic = decode.get_dictionary('ሴ/🜺\n\N{pisces}/♄\n\u3210/\u4444', False)
            self.assertEquals(dic, {'ሴ': '🜺', '㈐': '䑄', '♓': '♄'}, 'Unescaped unicode chars not handled correctly.')
        with self.subTest('Escaped unicode'):
            dic = decode.get_dictionary('\\u1234/\\U0001F73A\n\\N{pisces}/\\u2644\n\\u3210/\\u4444', False)
            self.assertEquals(dic, {'ሴ': '🜺', '㈐': '䑄', '♓': '♄'}, 'Escaped unicode characters not handled correctly.')

    def test_translate(self):
        with self.subTest('Basic functionality'):
            trans = decode.translate('abc\nabcdefg', {'a': 'b', 'c': 'd', 'e': 'f'})
            self.assertEquals(trans, 'bbd\nbbddffg', 'Basic substitution not working.')
        with self.subTest('Comments'):
            trans = decode.translate('#comment\nabc\nabcdefg #com', {'a': 'b', 'c': 'd', 'e': 'f'})
            self.assertEquals(trans, '#comment\nbbd\nbbddffg #com', 'Comments not processed correctly.')
        with self.subTest('Tags'):
            trans = decode.translate('ace<ace>\n[ace]ace', {'a': 'b', 'c': 'd', 'e': 'f'})
            self.assertEquals(trans, 'bdf<ace>\n[ace]bdf', 'Text in tags (cleartext) not processed correctly.')
        with self.subTest('Empty'):
            trans = decode.translate('', {'a': 'b', 'c': 'd', 'e': 'f'})
            self.assertEquals(trans, '', 'Empty strings not handled correctly.')
        with self.subTest('Chained substitution'):
            trans = decode.translate('abcde', {'a': 'b', 'c': 'b', 'b': 'f', 'd': 'b', 'e': 'b'})
            self.assertEquals(trans, 'bfbbb', 'Characters not only processed once.')
        with self.subTest('Greedy key matching'):
            for n in range(1, 10):  # Run several times as dict ordering can potentially be random
                trans = decode.translate('abcabc', {'bc': 'Q', 'ab': 'Y', 'abc': 'X', 'a': 'f', 'b': 'g'})
                self.assertEquals(trans, 'XX', 'Longer keys not processed before shorter ones.')
        with self.subTest('Unicode'):
            trans = decode.translate('aሴb㈐c\nd♓efľőêèå', {'ሴ': '🜺', '㈐': '䑄', '♓': '♄'})
            self.assertEquals(trans, 'a🜺b䑄c\nd♄efľőêèå', 'Unicode characters not handled correctly.')
        with self.subTest('Multiple inline comments/tags'):
            trans = decode.translate('#c\na[a]<a>a[a][a]#a\n<a>[a]a<a>a#a', {'a': 'b'})
            self.assertEquals(trans, '#c\nb[a]<a>b[a][a]#a\n<a>[a]b<a>b#a',
                              'Multiple comments/tags in one line not processed correctly.')

    def test_remove_comments(self):
        with self.subTest('Text without comments'):
            text = 'some text\nnew line\nmore text'
            self.assertEquals(text, decode.remove_comments(text), 'Text without comments not handled correctly')
        with self.subTest('Inline comments'):
            text = 'text #comment1\nnew line# comment2 \nmore text # comment3     '
            self.assertEquals('text \nnew line\nmore text ', decode.remove_comments(text),
                              'Inline comments not handled correctly')
        with self.subTest('Comment lines'):
            text = '#comment\ntext\nmore text'
            self.assertEquals('text\nmore text', decode.remove_comments(text),
                              'Comment lines not handled correctly')
        with self.subTest('Whitespace and empty lines'):
            text = '\n# c\nt#c\nt # c\n\n#c#c\nt'
            self.assertEquals('\nt\nt \n\nt', decode.remove_comments(text),
                              'Whitespace and empty lines not handled correctly')
        with self.subTest('translate->remove_comment = remove_comment->translate'):
            text = '#c\na[a]<a>a[a][a]#a\n<a>[a]a<a>a#a'
            dictionary = {'a': 'b'}
            self.assertEquals(decode.remove_comments(decode.translate(text, dictionary)),
                              decode.translate(decode.remove_comments(text), dictionary),
                              'The order of operations for translating and removing comment should be reversible')

    def test_remove_tags(self):
        with self.subTest('Tags []'):
            self.assertEquals('text', decode.remove_tags('[text]'), '[] tags not handled correctly')
        with self.subTest('Tags <>'):
            self.assertEquals('text', decode.remove_tags('<text>'), '<> tags not handled correctly')
        with self.subTest('Tags <cleartext ...>'):
            self.assertEquals('text', decode.remove_tags('<cleartext -text>'),
                              '<cleartext ...> tags not handled correctly')
        with self.subTest('Tags <cleartext ...>'):
            self.assertEquals('text', decode.remove_tags('<cleartext -text>'),
                              'Case insensitive removal of "<cleartext" tags not handled correctly')
        with self.subTest('Removing language attributes'):
            self.assertEquals('text', decode.remove_tags('<cleartext-LA text>'), 'Language tags not removed correctly')
        with self.subTest('Not removing text similar to language attributes'):
            self.assertEquals('te xt', decode.remove_tags('<cleartext-te xt>'),
                              'Language tags incorrectly identified and removed')
