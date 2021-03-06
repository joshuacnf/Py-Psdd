from structure.Psdd import *
from structure.Element import *
from structure.Sdd import *

import math
import random

def _satisfy(u, asgn, f):
    if u._idx in f:
        return f[u._idx]

    if u.is_terminal:
        if u._lit == 'F':
            f[u._idx] = False
            return False
        if u._lit == 'T':
            f[u._idx] = True
            return True
        if isinstance(u._lit, int):
            res = asgn[abs(u._lit)]
            if u._lit < 0:
                res = not res
            f[u._idx] = res
            return res

    for e in u._elements:
        if _satisfy(e._prime, asgn, f):
            if _satisfy(e._sub, asgn, f):
                f[u._idx] = True
                return True
            else:
                f[u._idx] = False
                return False

def _add_weight(u, asgn, w, f, g, h):
    if u._idx not in g:
        u._context_weight += w
        g[u._idx] = True
    if u.is_terminal:
        if u._lit == 'T':
            if asgn[list(u._vtree.variables)[0]] and (u._idx not in h):
                u._weight += w
                h[u._idx] = True
    else:
        for e in u._elements:
            p, s = e._prime, e._sub
            if (p._idx in f) and f[p._idx]:
                e._weight += w
                _add_weight(p, asgn, w, f, g, h)
                _add_weight(s, asgn, w, f, g, h)

def set_data(u, data):
    if data is not None:
        set_data(u, None)
        for asgn, w in data.items():
            f, g, h = {}, {}, {}
            _satisfy(u, asgn, f)
            _add_weight(u, asgn, w, f, g, h)

    if data is None:
        u._weight = 0.0
        u._context_weight = 0.0
        for e in u._elements:
            e._theta = 0.0
            e._weight = 0.0
            set_data(e._prime, None)
            set_data(e._sub, None)

def compute_parameter(u):
    ele_cnt = len(u._elements)
    for e in u._elements:
        p, s = e._prime, e._sub
        # e._theta = 0.0
        # if u._context_weight != 0.0:
        e._theta = (e._weight + 0.1) / (u._context_weight + ele_cnt * 0.1)
        compute_parameter(p)
        compute_parameter(s)

    if u.is_terminal and u._lit == 'T':
        u._theta = 0.5
        if u._context_weight != 0.0:
            u._theta = u._weight / u._context_weight

def compute_probability(u, asgn, cache):
    if u.idx in cache:
        return cache[u.idx]
    flag = False
    for x in u.vtree.variables:
        if asgn[x] is not None:
            flag = True
            break
    if flag == False:
        return 1.0

    res = None
    if u.is_terminal:
        if u._lit == 'F':
            res = 0.0

        if u._lit == 'T':
            v = list(u.vtree.variables)[0]
            res = u._theta if asgn[v] else (1.0 - u._theta)

        if isinstance(u._lit, int):
            v = abs(u._lit)
            sgn = 1 if u._lit > 0 else -1
            asgn_v = 1 if asgn[v] == True else -1
            res = 1.0 if sgn * asgn_v > 0 else 0.0
    else:
        res = 0.0
        for e in u._elements:
            p, s, theta = e._prime, e._sub, e._theta
            if theta != 0.0:
                res += compute_probability(p, asgn, cache) * compute_probability(s, asgn, cache) * theta
    cache[u.idx] = res
    return res

def compute_probability_batch(u, asgn_batch, cache):
    if u.idx in cache:
        return cache[u.idx]
    # flag = False
    # for x in u.vtree.variables:
    #     if asgn[x] is not None:
    #         flag = True
    #         break
    # if flag == False:
    #     return [ 1.0 for x in range(len(asgn_batch)) ]

    res = None
    if u.is_terminal:
        v = list(u.vtree.variables)[0]
        res = [ 0.0 for x in range(len(asgn_batch)) ]        
        if u._lit == 'F':            
            res = [ (asgn[v] == None) * 1.0 for asgn in asgn_batch ]
            # for idx, asgn in enumerate(asgn_batch):
                # res[idx] = u._theta

        if u._lit == 'T':
            # v = list(u.vtree.variables)[0]
            for idx, asgn in enumerate(asgn_batch):
                res[idx] = u._theta if asgn[v] or (asgn[v] is None) else (1.0 - u._theta)

        if isinstance(u._lit, int):
            # v = abs(u._lit)            
            sgn = 1 if u._lit > 0 else -1
            for idx, asgn in enumerate(asgn_batch):
                asgn_v = 1 if asgn[v] == True else -1
                res[idx] = 1.0 if (sgn * asgn_v > 0) or (asgn[v] is None) else 0.0
    else:
        res = [ 0.0 ] * len(asgn_batch)
        for e in u._elements:
            p, s, theta = e._prime, e._sub, e._theta            
            p_res = compute_probability_batch(p, asgn_batch, cache)
            s_res = compute_probability_batch(s, asgn_batch, cache)            
            ps_res = [ x * y for x, y in zip(p_res, s_res) ]
            ps_res = [ x * theta for x in ps_res ]
            res = [ x + y for x, y in zip(res, ps_res) ]            
    cache[u.idx] = res
    return res

def compute_log_likelihood(u, data):
    res = 0.0
    for asgn, w in data.items():
        res += w * math.log(compute_probability(u, asgn))
    return res

def EM(psdd0, psdd1, data):
    data0 = {}
    data1 = {}
    for asgn, w in data.items():
        q = random.gauss(0.5, 0.15)
        q = min(q, 0.99)
        q = max(q, 0.01)
        data0[asgn] = w * (1 - q)
        data1[asgn] = w * q

    set_data(psdd0, data0)
    set_data(psdd1, data1)
    compute_parameter(psdd0)
    compute_parameter(psdd1)

    for i in range(1000):
        # structure learning
        for j in range(50):
            W0, W1 = 0.0, 0.0
            for asgn, w in data0.items():
                W0 += w
            for asgn, w in data1.items():
                W1 += w
            p0 = W0 / (W0 + W1)
            p1 = W1 / (W0 + W1)

            for asgn, w in data.items():
                q0 = compute_probability(psdd0, asgn)
                q1 = compute_probability(psdd1, asgn)
                r0 = q0 * p0
                r1 = q1 * p1
                w0 = r0 / (r0 + r1)
                w1 = r1 / (r0 + r1)
                data0[asgn] = w0 * w
                data1[asgn] = w1 * w

            set_data(psdd0, data0)
            set_data(psdd1, data1)
            compute_parameter(psdd0)
            compute_parameter(psdd1)

def re_index(u, next_idx=0):
    u._idx = next_idx
    next_idx += 1
    for p, s in u._elements:
        next_idx = re_index(p, next_idx)
        next_idx = re_index(s, next_idx)
    return next_idx

def negate(u):
    if u.is_terminal:
        if isinstance(u._lit, int):
            u._lit = -u._lit
        if u._lit == 'T':
            u._lit = 'F'
        if u._lit == 'F':
            u._lit = 'T'
        return None

    for p, s in u._elements:
        negate(s)

def apply(u1, u2, op, cache): # bug with cache
    idx1, idx2 = u1.idx, u2.idx
    if (idx1, idx2, op) in cache:
        return cache[(idx1, idx2, op)]

    if u1.is_terminal and u2.is_terminal:
        b = None
        b1, b2 = u1._lit, u2._lit
        if isinstance(b2, int):
            b1, b2 = b2, b1

        if isinstance(b1, int):
            if isinstance(b2, int):
                if op == 'AND':
                    b = 'F' if b1 == -b2 else b1
                if op == 'OR':
                    b = 'T' if b1 == -b2 else b1
            else:
                if op == 'AND':
                    b = b1 if b2 == 'T' else 'F'
                if op == 'OR':
                    b = 'T' if b2 == 'T' else b1
        else:
            if op == 'AND':
                b = 'F' if b1 == 'F' else b2
            if op == 'OR':
                b = 'T' if b1 == 'T' else b2

        res = Sdd(0, b, u1.vtree)
        cache[(idx1, idx2, op)] = res
        return res

    res = Sdd(0, None, u1.vtree)
    for p, s in u1._elements:
        for q, t in u2._elements:
            r = apply(p, q, 'AND', cache)
            u = apply(s, t, op, cache)
            res.add_element((r, u))

    cache[(idx1, idx2, op)] = res
    return res

def normalize(u, v, cache_lit, cache_idx):
    if v.left is None:
        u.vtree = v
        return u

    res = None
    lit = u.lit
    idx = u.idx
    if lit is not None:
        if v.idx in cache_lit:
            if lit in cache_lit[v.idx]:
                return cache_lit[v.idx][lit]
        else:
            cache_lit[v.idx] = {}
    if idx != -1:
        if v.idx in cache_idx:
            if idx in cache_idx[v.idx]:
                return cache_idx[v.idx][idx]
        else:
            cache_idx[v.idx] = {}

    if lit == 'T' or lit == 'F':
        res = Sdd()
        res.vtree = v
        res.add_element((Sdd(-1, 'T', v.left), Sdd(-1, u.lit, v.right)))
    elif u.vtree.idx != v.idx:
        w = u.vtree
        while w.parent.idx != v.idx:
            w = w.parent

        res = Sdd()
        res.vtree = v
        if v.left.idx == w.idx:
            p1, p2 = u, u.copy()
            negate(p2)
            res.add_element((p1, Sdd(-1, 'T', v.right)))
            res.add_element((p2, Sdd(-1, 'F', v.right)))

        if v.right.idx == w.idx:
            res.add_element((Sdd(-1, 'T', v.left), u))
    else:
        res = u

    tmp = []
    for p, s in res._elements:
        q = normalize(p, res.vtree.left, cache_lit, cache_idx)
        t = normalize(s, res.vtree.right, cache_lit, cache_idx)
        tmp.append((q, t))
    res._elements = tmp

    if lit is not None:
        cache_lit[v.idx][lit] = res
    if idx != -1:
        cache_idx[v.idx][idx] = res

    return res

def compile(cnf, vtree):
    def f(v):
        if v.is_terminal:
            return { v._var: v }
        return { **f(v.left), **f(v.right) }
    m = f(vtree)

    def test(x):
        if (len(x._elements) == 0) and (x._lit == None):
            return 'ERROR'
        for p, s in x._elements:
            res = test(p)
            if res is not None:
                return res
            res = test(s)
            if res is not None:
                return res
        return None

    cache_lit, cache_idx = {}, {}
    ri = Sdd(0, 'T')
    ri = normalize(ri, vtree, cache_lit, cache_idx)
    ri._node_count = re_index(ri)
    for clause in cnf:
        rj = Sdd(0, 'F')
        cache_lit, cache_idx = {}, {}
        rj = normalize(rj, vtree, cache_lit, cache_idx)
        rj._node_count = re_index(rj)
        for lit in clause:
            rk = Sdd(0, lit, m[abs(lit)])
            cache_lit, cache_idx = {}, {}
            rk = normalize(rk, vtree, cache_lit, cache_idx)
            rk._node_count = re_index(rk)

            cache_lit, cache_idx = {}, {}
            rj = apply(rj, rk, 'OR', cache_lit, cache_idx)
            rj._node_count = re_index(rj)

        cache_lit, cache_idx = {}, {}
        ri = apply(ri, rj, 'AND', cache)
        ri._node_count = re_index(ri)

    return ri