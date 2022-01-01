import re
import enum

class Complete:
	__slots__ = ('value', 'remainder')
	def __init__(self, value, remainder):
		self.value = value
		self.remainder = remainder
	def is_complete(self):
		return True

class Partial:
	__slots__ = ('kind',)
	def __init__(self, kind):
		self.kind = kind
	def is_complete(self):
		return False

class Compose:
	__slots__ = ('kind', 'parts')

	def __init__(self, kind, *parts):
		self.kind = kind
		self.parts = parts

	def __call__(self, func):
		def bt(l, i, string):
			if i >= len(self.parts):
				args = []
				for arg in l:
					if arg.is_complete():
						args.append(arg)
					else:
						yield Partial(kind)
						return
				yield Complete(func(*args), string)
			elif string == "":
				yield Partial(kind)
			else:
				l.append(None)
				for result, rem in self.parts[i](string):
					l[-1] = result.value
					yield from bt(l, i + 1, rem)
				l.pop()

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
			yield (s, string[len(s):])
	return opts

def regex(s):
	s = re.compile(s)
	def opts(string):
		m = re.match(s, string)
		if m:
			yield (string[:m.end()], string[m.end():])
	return opts

def empty(string):
	yield (None, string)

def many(p):
	def bt(l, string):
		l.append(None)
		for value, rem in p(string):
			l[-1] = value
			yield from opts(rem)
			yield (l[:], rem)
		l.pop()

	def opts(string):
		yield from bt([], string)

	return opts

def pair(p1, p2):
	def opts(string):
		for v1, r1 in p1(string):
			for v2, r2 in p2(r1):
				yield ((v1, v2), r2)
	return opts

def between(pb, p, pa):
	def opts(string):
		for vb, rb in pb(string):
			for v, r in p(rb):
				for va, ra in pa(r):
					yield (v, r)
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
	v = a
	for op, lit in bs:
		if op == "/":
			v /= int(lit)
		else:
			v *= int(lit)
	return v

