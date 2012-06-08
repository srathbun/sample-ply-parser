'''
File: Lexer.py
Author: Spencer Rathbun
Date: 05/07/2012
Description: Lexer. Originally built off of the C lexer: http://code.google.com/p/pycparser/source/browse/pycparser/c_lexer.py
'''

import re
import sys
import string

import ply.lex
from ply.lex import TOKEN

def printme(inputList):
	for item in inputList:
		print item

class Lexer(object):
	""" A lexer for input files. After building it, set the
		input text with input(), and call token() to get new
		tokens.

		The public attribute filename can be set to an initial
		filaneme, but the lexer will update it upon #line
		directives.
	"""
	def __init__(self, error_func, type_lookup_func, filename=None):
		""" Create a new Lexer.

			error_func:
				An error function. Will be called with an error
				message, line and column as arguments, in case of
				an error during lexing.

			type_lookup_func:
				A type lookup function. Given a string, it must
				return True IFF this string is a name of a type
				that was defined with a typedef earlier.
		"""
		self.error_func = error_func
		self.type_lookup_func = type_lookup_func
		if filename != None:
			self.filename = filename
		else:
			self.filename = ''

	def build(self, **kwargs):
		""" Builds the lexer from the specification. Must be
			called after the lexer object is created.

			This method exists separately, because the PLY
			manual warns against calling lex.lex inside
			__init__
		"""
		self.lexer = ply.lex.lex(object=self, **kwargs)

	def tabfile(self, tabfile, outputdir=""):
		""" Build a tabfile from the lexer."""
		self.lexer.writetab(tabfile, outputdir=outputdir)

	def reset_lineno(self):
		""" Resets the internal line number counter of the lexer.
		"""
		self.lexer.lineno = 1

	def input(self, text):
		self.lexer.input(text)

	def token(self):
		g = self.lexer.token()
		return g

	######################--   PRIVATE   --######################

	##
	## Internal auxiliary methods
	##
	def _error(self, msg, token):
		location = self._make_tok_location(token)
		self.error_func(msg, location[0], location[1])
		self.lexer.skip(1)

	def _find_tok_column(self, token):
		i = token.lexpos
		while i > 0:
			if self.lexer.lexdata[i] == '\n': break
			i -= 1
		return (token.lexpos - i) + 1

	def _make_tok_location(self, token):
		return (token.lineno, self._find_tok_column(token))

	##
	## All the tokens recognized by the lexer
	##
	tokens = (
			'TEXT', 'WHITESPACE', 'LINENO', 'NUMBER', 'STARTADDRESS', 'ENDADDRESS', 'STARTPAGE'
	)

	##
	## Regexes for use in tokens
	##
	##

	STARTADDRESS   = r'\w+[ ]+\d+,[ ]+\d+[ ]+to[ ]+\w+[ ]+\d+,[ ]+\d+'
	ENDADDRESS     = r'\*+[ ]Summary[ ]of[ ]Account[ ]Activity[ ]\*+'
	TEXT           = r'[{0}]+'.format(string.printable.translate(None, '0123456789 \t\n'))
	WHITESPACE     = r'\s+'
	NUMBER         = r'\d+'
	LINENO         = r'\s*\d+\n'
	STARTPAGE = r'\s*000000001\n'

	##
	## Lexer states
	##
	states = (
	)


	@TOKEN(STARTPAGE)
	def t_STARTPAGE(self, t):
		return t

	@TOKEN(LINENO)
	def t_LINENO(self, t):
		t.lexer.lineno += t.value.count("\n")
		return t

	@TOKEN(STARTADDRESS)
	def t_STARTADDRESS(self, t):
		return t

	@TOKEN(ENDADDRESS)
	def t_ENDADDRESS(self, t):
		return t

	@TOKEN(WHITESPACE)
	def t_WHITESPACE(self, t):
		return t

	@TOKEN(NUMBER)
	def t_NUMBER(self, t):
		return t

	@TOKEN(TEXT)
	def t_TEXT(self, t):
		return t

	def t_error(self, t):
		msg = 'Illegal character %s' % repr(t.value[0])
		self._error(msg, t)


if __name__ == "__main__":
	filename = 'test'
	text = open(filename).read()

	def errfoo(msg, a, b):
		sys.stderr.write(msg + "\n")
		sys.exit()

	def typelookup(namd):
		return False

	lex = Lexer(errfoo, typelookup, filename=filename)
	lex.build(debug=1)
	lex.tabfile("tabfile")
	lex.input(text)

	while 1:
		tok = lex.token()
		if not tok: break

		#~ print type(tok)
		printme([tok.value, tok.type, tok.lineno, lex.filename, tok.lexpos])

