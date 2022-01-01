import re
import enum

class Compose:
	__slots__ = ('parts')

	def __init__(self, *parts):
		self.parts = parts

	def __call__(self, func):
		def bt(l, i, location, string):
			if i >= len(self.parts):
				yield (func(*l), location, string)
			else:
				l.append(None)
				for value, loc, remainder in self.parts[i](location, string):
					l[-1] = value
					yield from bt(l, i + 1, loc, remainder)
				l.pop()

		def opts(location, string):
			yield from bt([], 0, location + [func.__name__], string)

		return opts

def choice(p1, p2):
	def opts(location, string):
		yield from p1(location, string)
		yield from p2(location, string)
	return opts

def string(s):
	def opts(location, string):
		if string.startswith(s):
			yield (s, location, string[len(s):])
	return opts

def regex(s):
	s = re.compile(s)
	def opts(location, string):
		m = re.match(s, string)
		if m:
			yield (string[:m.end()], location, string[m.end():])
	return opts

def empty(location, string):
	yield (None, location, string)

def unit(value):
	def opts(location, string):
		yield (value, location, string)
	return opts

def some(p):
	def bt(vs, location, string):
		vs.append(None)
		for v, l, r in p(location, string):
			vs[-1] = v
			yield from bt(vs, l, r)
			yield (vs[:], l, r)
		vs.pop()

	def opts(location, string):
		yield from bt([], location, string)

	return opts

def many(p):
	return choice(some(p), unit([]))

def pair(p1, p2):
	def opts(location, string):
		for v1, l1, r1 in p1(location, string):
			for v2, l2, r2 in p2(l1, r1):
				yield ((v1, v2), l2, r2)
	return opts

def between(pb, p, pa):
	def opts(location, string):
		for vb, lb, rb in pb(location, string):
			for v, l, r in p(lb, rb):
				for va, la, ra in pa(l, r):
					yield (v, l, ra)
	return opts

# Parser :: String -> [(a, String)]
# bind :: (String -> [(a, String)])
#      -> (a -> String -> [(b, String)])
#      -> (String -> [(b, String)])

literal = Compose(regex('[0-9]+'))(int)

prodop = choice(string("*"), string("/"))

@Compose(literal, many(pair(prodop, literal)))
def product(a, bs):
	for op, lit in bs:
		if op == "/":
			a /= lit
		else:
			a *= lit
	return a

addop = choice(string("+"), string("-"))

@Compose(product, many(pair(addop, product)))
def term(a, bs):
	for op, lit in bs:
		if op == "+":
			a += lit
		else:
			a -= lit
	return a

def parse(parser, string):
	return list(parser([], string))

