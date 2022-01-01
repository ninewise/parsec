import re
import enum

class Complete:
	__slots__ = ('value', 'remainder')
	def __init__(self, value, remainder):
		self.value = value
		self.remainder = remainder
	def is_complete(self):
		return True
	def __repr__(self):
		return f'Complete({repr(self.value)}, {repr(self.remainder)})'

class Partial:
	__slots__ = ('location',)
	def __init__(self, location):
		self.location = location
	def is_complete(self):
		return False
	def __repr__(self):
		return f'Partial({repr(self.location)})'

class Compose:
	__slots__ = ('partial', 'parts')

	def __init__(self, *parts, partial=True):
		self.partial = partial
		self.parts = parts

	def __call__(self, func):
		def bt(l, i, string):
			if i >= len(self.parts):
				yield Complete(func(*l), string)
			else:
				partials = []
				l.append(None)
				for result in self.parts[i](string):
					if result.is_complete():
						l[-1] = result.value
						yield from bt(l, i + 1, result.remainder)
						partials = None
					elif partials is not None:
						partials.append(result.location)
				l.pop()
				if partials is not None and self.partial:
					for partial in partials:
						partial = partial + [func.__name__]
						yield Partial(partial)
					if not partials:
						yield Partial([func.__name__])

		def opts(string):
			yield from bt([], 0, string)

		return opts

def choice(p1, p2):
	def opts(string):
		yield from p1(string)
		yield from p2(string)
	return opts

def string(s):
	def opts(string):
		if string.startswith(s):
			yield Complete(s, string[len(s):])
	return opts

def regex(s):
	s = re.compile(s)
	def opts(string):
		m = re.match(s, string)
		if m:
			yield Complete(string[:m.end()], string[m.end():])
	return opts

def empty(string):
	yield Complete(None, string)

def unit(value):
	def opts(string):
		yield Complete(value, string)
	return opts

def some(p):
	def bt(l, string):
		l.append(None)
		for result in p(string):
			if result.is_complete():
				l[-1] = result.value
				yield from bt(l, result.remainder)
				yield Complete(l[:], result.remainder)
		l.pop()

	def opts(string):
		yield from bt([], string)

	return opts

def many(p):
	return choice(some(p), unit([]))

def pair(p1, p2):
	def opts(string):
		for r1 in p1(string):
			if not r1.is_complete(): continue
			for r2 in p2(r1.remainder):
				if not r2.is_complete(): continue
				yield Complete((r1.value, r2.value), r2.remainder)
	return opts

def between(pb, p, pa):
	def opts(string):
		for rb in pb(string):
			if not rb.is_complete(): continue
			for r in p(rb.remainder):
				if not r.is_complete(): continue
				for ra in pa(r.remainder):
					if not ra.is_complete(): continue
					yield Complete(v.value, ra.remainder)
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

