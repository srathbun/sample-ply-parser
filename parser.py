#!/usr/bin/env python
'''
Project: Parser
Author: Spencer Rathbun
Date: 1/24/2012
Summary: Parser. See the readme for details. Originally from http://code.google.com/p/pyparser/source/browse/pycparser/c_parser.py
'''
import re, logging
import ply.yacc

from Lexer import Lexer
from Helpers import PLYParser


class Parser(PLYParser):
	def __init__(
			self,
			lex_optimize=True,
			lextab='pyparser.lextab',
			yacc_optimize=True,
			yacctab='pyparser.yacctab',
			yacc_debug=False):
		""" Create a new parser.

			Some arguments for controlling the debug/optimization
			level of the parser are provided. The defaults are
			tuned for release/performance mode.
			The simple rules for using them are:
			*) When tweaking the lexer/parser, set these to False
			*) When releasing a stable parser, set to True

			lex_optimize:
				Set to False when you're modifying the lexer.
				Otherwise, changes in the lexer won't be used, if
				some lextab.py file exists.
				When releasing with a stable lexer, set to True
				to save the re-generation of the lexer table on
				each run.

			lextab:
				Points to the lex table that's used for optimized
				mode. Only if you're modifying the lexer and want
				some tests to avoid re-generating the table, make
				this point to a local lex table file (that's been
				earlier generated with lex_optimize=True)

			yacc_optimize:
				Set to False when you're modifying the parser.
				Otherwise, changes in the parser won't be used, if
				some parsetab.py file exists.
				When releasing with a stable parser, set to True
				to save the re-generation of the parser table on
				each run.

			yacctab:
				Points to the yacc table that's used for optimized
				mode. Only if you're modifying the parser, make
				this point to a local yacc table file

			yacc_debug:
				Generate a parser.out file that explains how yacc
				built the parsing table from the ammar.
		"""
		self.logger = logging.getLogger('parser')
		self.lex = Lexer(
			error_func=self._lex_error_func,
			type_lookup_func=self._lex_type_lookup_func)

		self.lex.build(
			optimize=lex_optimize,
			lextab=lextab)
		self.tokens = self.lex.tokens

		self.parser = ply.yacc.yacc(
			module=self,
			start='statements',
			debug=yacc_debug,
			optimize=yacc_optimize,
			tabmodule=yacctab)

		self.addresses = []
		self.accounts = {}
		self.statements = 0
		self.totalPages = 0

		self.pdf_doc = PDFDoc()
		self.pdf_doc.InitSecurityHandler()
		self.timesRoman = Font.Create(self.pdf_doc.GetSDFDoc(), Font.e_times_roman, True)
		self.courierNew = Font.Create(self.pdf_doc.GetSDFDoc(), Font.e_courier, True)
		self.eb = ElementBuilder()
		self.writer = ElementWriter()

	def parse(self, text, filename='', debuglevel=0):
		""" Parses a file and returns a pdf.

			text:
				A string containing the C source code

			filename:
				Name of the file being parsed (for meaningful
				error messages)

			debuglevel:
				Debug level to yacc
		"""
		self.lex.filename = filename
		self.lex.reset_lineno()
		self._scope_stack = [set()]
		self.logger.info("_______________________________________________")
		self.logger.info("parsing input...")
		if not text or text.isspace():
			return []
		else:
			self.logger.info("_______________________________________________")
			self.logger.info("finished parsing input file...")
			return self.parser.parse(text, lexer=self.lex, debug=debuglevel)

	######################--   PRIVATE   --######################

	##
	## Precedence and associativity of tokens
	##
	precedence = (
			('left', 'LINENO'),
			('left', 'STARTPAGE'),
	)

	def _lex_error_func(self, msg, line, column):
		self._parse_error(msg, self._coord(line, column))

	def _lex_type_lookup_func(self, name):
		""" Looks up types that were previously defined with
			typedef.
			Passed to the lexer for recognizing identifiers that
			are types.
		"""
		return self._is_type_in_scope(name)

	def p_empty(self, p):
		'empty : '
		p[0] = ''

	def p_error(self, p):
		if p:
			self._parse_error(
				'before: %s' % p.value,
				self._coord(p.lineno))
		else:
			self._parse_error('At end of input', '')

	def p_statements(self, p):
		'''statements : statements pagelist
                      | pagelist'''
		pass

	def p_pagelist(self, p):
		'''pagelist : addrpage
                    | page'''
		pass

	def p_addrpage(self, p):
		'''addrpage : STARTPAGE lines address lines'''
		if self.addresses[-1].find('******************') == -1:
			self.totalPages += 1
			self.statements += 1
			pagestr = ''
			for s in p[2:]:
				pagestr = "{0}{1}".format(pagestr, s)
			self.buildNewPage(pagestr)

			# add new entry to accts
			self.accounts[str(self.statements)] = [1, [str(self.totalPages)], self.addresses[-1], [], None]

	def p_page(self, p):
		'''page : STARTPAGE lines'''
		if self.addresses[-1].find('******************') == -1:
			self.totalPages += 1
			pagestr = ''
			for s in p[2:]:
				pagestr = "{0}{1}".format(pagestr, s)
			self.buildNewPage(pagestr)
			self.accounts[str(self.statements)][0] = self.accounts[str(self.statements)][0] + 1
			self.accounts[str(self.statements)][1].append(str(self.totalPages))

	def p_address(self, p):
		'''address : beginaddress lines stopaddress'''
		self.addresses.append(p[2])
		p[0] = "{0}{1}{2}".format(p[1], p[2], p[3])

	def p_lines(self, p):
		'''lines : lines line
                 | line'''
		if len(p) > 2:
			p[0] = "{0}{1}".format(p[1], p[2])
		else:
			p[0] = p[1]

	def p_line(self, p):
		'''line : linedata LINENO
		        | LINENO'''
		if len(p) == 3:
			p[0] = "{0}\n".format(p[1])
		else:
			p[0] = "\n"

	def p_linedata(self, p):
		'''linedata : linedata WHITESPACE
				| linedata NUMBER
				| linedata TEXT
				| empty'''
		if len(p) == 3:
			p[0] = "{0}{1}".format(p[1], p[2])
		else:
			p[0] = "{0}".format(p[1])

	def p_beginaddress(self, p):
		'''beginaddress : linedata STARTADDRESS LINENO
                        | linedata STARTADDRESS linedata LINENO'''
		if len(p) == 4:
			p[0] = "{0}{1}\n".format(p[1], p[2])
		else:
			p[0] = "{0}{1}{2}\n".format(p[1], p[2], p[3])

	def p_stopaddress(self, p):
		'''stopaddress : linedata ENDADDRESS LINENO
                       | linedata ENDADDRESS linedata LINENO'''
		if len(p) == 4:
			p[0] = "{0}{1}\n".format(p[1], p[2])
		else:
			p[0] = "{0}{1}{2}\n".format(p[1], p[2], p[3])


	######################--   PDF BUILDING    --################

	def buildNewPage(self, pagestr):
		"""Create a new page and add the string contents as text elements."""
		self.logger.debug("building page {0}...".format(self.totalPages))
		page = self.pdf_doc.PageCreate(Rect(0, 0, 612, 794))
		self.writer.Begin(page)
		self.eb.Reset()

		# begin writing text elements to the current page
		element = self.eb.CreateTextBegin(self.courierNew, 8)
		element.SetTextMatrix(1, 0, 0, 1, 30, 750) # last two digits are x, y coords on page measured from LOWER RIGHT corner
		self.writer.WriteElement(element)

		# loop over the split string and write each line
		for item in pagestr.split('\n'):
			element = self.eb.CreateTextRun(item)
			element.GetGState().SetLeading(10)         # Set the spacing between lines
			self.writer.WriteElement(element)
			self.writer.WriteElement(self.eb.CreateTextNewLine())

		self.writer.WriteElement(self.eb.CreateTextEnd())
		self.writer.End()
		# add the page to the document
		self.pdf_doc.PagePushBack(page)

	def savePDF(self, filename):
		"""Save the current pdf with the input filename."""
		self.logger.debug("saving {0}...".format(filename))
		self.pdf_doc.Save(filename, SDFDoc.e_compatibility)

	def closePDF(self):
		"""Close the current pdf."""
		self.pdf_doc.Close()

#------------------------------------------------------------------------------
if __name__ == "__main__":
	PDFNet.Initialize('L & D Mail Masters(ldmailmasters.com):CPU:1::W:AMC(20120118):3D4E42F925150FCAF1B425461F9C92CA03BA1CA4C9900B3699D039F1F0FA')
	filename = 'test data/Gold Reserve -test file.txt'
	text = open(filename).read()
	parser = Parser(lex_optimize=False, yacc_debug=True, yacc_optimize=False)
	#sys.write(time.time() - t1)

	#buf = '''
		#int (*k)(int);
	#'''

	## set debuglevel to 2 for debugging
	t = parser.parse(text, filename=filename, debuglevel=2)
	parser.savePDF('test.pdf')
	parser.closePDF()

