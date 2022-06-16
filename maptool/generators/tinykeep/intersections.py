"""Insert intersections and clip corridors to reconcile partialy co-incident corridors

"""
from collections import namedtuple
from dataclasses import dataclass
from maptool import geometry as g
from maptool.room import Room, RoomSide
from maptool.corridor import Corridor

# cainv, cbinv: indicate if the respective corridors are inverted: runing right
# to left or running north to south is classed as inverted.
MergeCase = namedtuple("MergeCase", "cainv cbinv".split())
# cai and cbi indicate the index into join & join_sides representing R1
Merge = namedtuple("MergeSelect", "cai cbi".split(), defaults=(None, None))

class GenerateIntersections:

    STRAIGHT_CASES = {

        #   +--ca--------> R2
        # R1                      R1 cb R3 R2
        #   +--cb---> R3
        #
        #  r1.detach(ca) -> rdetside
        #  ca.p[0] = cb.p[1]
        #  ca.j[0] = cb.j[1]
        #  r3.attach(ca, opp(rdetside))
        MergeCase(cainv=0, cbinv=0): Merge(
            cai=0, cbi=0),

        #   +--ca--------> R2
        # R1                      R1 cb R3 R2
        #   <--cb---+ R3
        #
        #  r1.detach(ca) -> rdetside
        #  ca.p[0] = cb.p[0]
        #  ca.j[0] = cb.j[0]
        #  r3.attach(ca, opp(rdetside))
        MergeCase(cainv=0, cbinv=1): Merge(
            cai=0, cbi=1),

        #   <--ca--------+ R2
        # R1                      R1 cb R3 R2
        #   +--cb---> R3
        #
        #  r1.detach(ca) -> rdetside
        #  ca.p[0] = cb.p[1]
        #  ca.j[0] = cb.j[1]
        #  r3.attach(ca, opp(rdetside))
        MergeCase(cainv=1, cbinv=0): Merge(
            cai=1, cbi=0),

        #   <--ca--------+ R2
        # R1                      R1 cb  R3 ca  R2
        #   <--cb---+ R3
        #
        #  r1.detach(ca) -> rdetside
        #  ca.p[1] = cb.p[1]
        #  ca.j[1] = cb.j[1]
        #  r3.attach(ca, opp(rdetside))
        MergeCase(cainv=1, cbinv=1): Merge(
            cai=1, cbi=1),
    }

    LL_CASES = {
        #                 ^
        #                 |R2
        # R1 +--ca--------.
        #    +--cb---.
        #            | R3
        #            `
        # ir1  = cb.join[0]
        # r1   = rooms[ir1]
        # rn.c = cb.points[1]
        # irn = len(rooms)
        #
        # cn.p[0] = cb.points[0]
        # cn.p[1] = cb.points[1]
        # cn.joins[0] = cb.joins[0]
        # cn.joins[1] = irn
        # cn.join_sides[0] = cb.join_sides[0]
        # cn.join_sides[1] = opposite(cb.join_sides[0])
        #
        # cb.points  = cb.points[1:3]
        # cb.join[0] = irn
        # cb.join_sides[0] = opp(cb.join_sides[1])
        # rn.corridors[opp(cb.join_sides[1])].append(jcor)


        MergeCase(cainv=0, cbinv=0): Merge(
            cai=0, cbi=0),

        #                 ^
        #                 |R2
        # R1 +--ca--------.
        #    <--cb---.
        #            | R3
        #            +
        MergeCase(cainv=0, cbinv=1): Merge(
            cai=0, cbi=1),

        #                 +
        #                 |R2
        # R1 <--ca--------.
        #    +--cb---.
        #            | R3
        #            `
        MergeCase(cainv=1, cbinv=0): Merge(
            cai=1, cbi=0),

        #                 +
        #                 |R2
        # R1 <--ca--------.
        #    <--cb---.
        #            | R3
        #            +
        MergeCase(cainv=1, cbinv=1): Merge(
            cai=1, cbi=1)
    }


    def __init__(self, rooms, corridors):
        self.rooms = rooms
        self.corridors = corridors

    # ---
    def _classify_ll_merge(self, icor, jcor) -> MergeCase:

        ca = self.corridors[icor]
        cb = self.corridors[jcor]

        if len(ca.points) != 3 or len(cb.points) != 3:
            raise ValueError("_classify_ll_merge needs two L corridors")

        if g.pt_essentially_same(ca.points[0], cb.points[0]):
            return MergeCase(cainv=0, cbinv=0)
        
        if g.pt_essentially_same(ca.points[0], cb.points[-1]):
            return MergeCase(cainv=0, cbinv=1)

        if g.pt_essentially_same(ca.points[-1], cb.points[0]):
            return MergeCase(cainv=1, cbinv=0)
        if g.pt_essentially_same(ca.points[-1], cb.points[-1]):
            return MergeCase(cainv=1, cbinv=1)

        raise ValueError("no co-incident points, corridors are not entanbled")


    def _classify_straight_merge(self, icor, jcor) -> MergeCase:

        ca = self.corridors[icor]
        cb = self.corridors[jcor]

        if len(ca.points) != 2 or len(cb.points) != 2:
            raise ValueError("_classify_straight_merge needs two straight corridors")

        cainv = cbinv = 1

        if ca.join_sides[0] in [g.LEFT, g.RIGHT]:

            if g.essentially_lt(ca.points[0].x, ca.points[1].x):
                # not inverted, normal is reading order. lower x first
                cainv = 0

            if g.essentially_lt(cb.points[0].x, cb.points[1].x):
                # not inverted, normal is reading order. lower x first
                cbinv = 0
            return MergeCase(cainv, cbinv)

        # lower y is 'north'. north -> south is inverted.
        if g.essentially_lt(ca.points[1].y, ca.points[0].y):
            # second point has lower y, not inverted
            cainv = 0
        if g.essentially_lt(cb.points[1].y, cb.points[0].y):
            cbinv = 0

        return MergeCase(cainv, cbinv)

    def _merge_straights(self, icor, jcor):

        case = self._classify_straight_merge(icor, jcor)
        m = self.STRAIGHT_CASES[case]
        ca = self.corridors[icor]
        cb = self.corridors[jcor]

        rd = ca.joins[m.cai]
        ir3 = cb.joins[1 - m.cbi]
        r3 = self.rooms[ir3]
        rdetside = rd.detach_corridor(icor)
        ca.points[m.cai] = cb.points[1 - m.cbi].clone()
        ca.joins[m.cai] = ir3
        #r3.corridors[RoomSide.opposite(rdetside)].append(icor)
        r3.corridors[rdetside].append(icor)

    def _merge_ll(self, icor, jcor):

        case = self._classify_ll_merge(icor, jcor)
        m = self.LL_CASES[case]
        ca = self.corridors[icor]
        cb = self.corridors[jcor]

        # deal with cb (jcor) first as we create the new intersection based on its mid point.

        # remove the start of cb from R1, create the intersection RN, convert cb
        # to a straight, attach the remaining leg of cb to RN

        ir1 = cb.joins[m.cbi]
        r1 = self.rooms[ir1]
        r1.detach_corridor(jcor)
        rn = Room()  # intersection
        rn.is_intersection = True
        rn.center = cb.points[1]
        irn = len(self.rooms)
        self.rooms.append(rn)

        # insert the new corridor segment replacing the co-incident sections of the entangled pair

        # cn.p[0] = cb.points[0]
        # cn.p[1] = cb.points[1]
        # cn.joins[0] = cb.joins[0]
        # cn.joins[1] = irn
        # cn.join_sides[0] = cb.join_sides[0]
        # cn.join_sides[1] = opposite(cb.join_sides[0])
        cn = Corridor(
            points=[None, None],
            joins=[None, None],
            join_sides=[None, None],
            is_inserted=True
        )

        # cn is a straight so we don't need to double cbi to get the right index into points
        cn.points[m.cbi] = cb.points[m.cbi * 2].clone() 
        cn.points[1 - m.cbi] = cb.points[1].clone()

        cn.joins[m.cbi] = cb.joins[m.cbi] 
        cn.join_sides[m.cbi] = cb.join_sides[m.cbi]
        cn.joins[1 - m.cbi] = irn
        cn.join_sides[1 - m.cbi] = RoomSide.opposite(cb.join_sides[m.cbi])
        icn = len(self.corridors)

        self.corridors.append(cn)

        # connect the new corridor to the rooms
        r1.corridors[cn.join_sides[m.cbi]].append(icn)
        rn.corridors[cn.join_sides[1 - m.cbi]].append(icn)

        cb.joins[m.cbi] = irn
        cb.join_sides[m.cbi] = RoomSide.opposite(cb.join_sides[1-m.cbi])
        cb.points = cb.points[(1-m.cbi):2+(1-m.cbi)]
        cb.clipped += 1

        rn.corridors[cb.join_sides[m.cbi]].append(jcor)

        # now deal with ca
        # truncate the R1 end of ca and attach it to RN
        r1side = r1.detach_corridor(icor)
        ca.points[m.cai] = rn.center.clone()
        ca.clipped += 1
        ca.joins[m.cai] = irn
        # join side from R1 is preserved on RN
        rn.corridors[r1side].append(icor)

    # ---
    def find_first_entangled_corridor_pair(self):
        for i, r in enumerate(self.rooms):

            for side in range(4):
                side_corridors = set(r.corridors[side])
                if len(side_corridors) <= 1:
                    continue

                # for each pair m, n of corridors see if they are actually
                # co-incident.  corridors joining intersections will touch as
                # intersections have zero widith & length so we need on point of
                # co-incidence plust another on the same x or same y as the co-incident

                for ic in side_corridors:
                    for jc in side_corridors:
                        if ic == jc:
                            continue

                        if not self.corridors[ic].check_entangled(self.corridors[jc]):
                            continue

                        return ic, jc

    def generate_corridor_intersection(self, ic, jc):
        """merge a single pair of entangled corridors"""

        c1, c2 = self.corridors[ic], self.corridors[jc]
        if not c1.check_entangled(c2):
            print(f"{ic} & {jc} are not entangled")
            return False


        if len(c1.points) == 3 and len(c2.points) == 3:
            self._merge_ll(ic, jc)
            assert not c1.check_entangled(c2)
            return True

        if len(c1.points) == 3 and len(c2.points) == 2:
            self._corridor_lmergehv(ic, jc)
            if c1.check_entangled(c2):
                print('xxx')

            return True

        if len(c1.points) == 2 and len(c2.points) == 3:
            self._corridor_lmergehv(jc, ic)
            if c1.check_entangled(c2):
                print('xxx')

            return True

        if len(c1.points) == 2 and len(c2.points) == 2:
            self._merge_straights(ic, jc)
            assert not c1.check_entangled(c2)
            return True


    # ---

    # ---
    def _corridor_lmerge(self, icor, jcor):
        """

        strategy: find the 'short' L spur and insert a new room at that point.
        mark the room as an intersection so we can handle it (in the
        content/game layer) distinctly from actual rooms


        L,L staggered

                +1
                |
        0+------+
            |    <-- spur
            +1

        L,L even
                +1
                | <- spur a
        0+------+
                | <- spur b (can pick either)
                +1

        """

        self._merge_ll(icor, jcor)

        # if its the even case pick c
        ci = self.corridors[icor]
        cj = self.corridors[jcor]

        if len(ci.points) != 3 and len(cj.points) != 3:
            raise ValueError("corridor_lmerge requires two elbows")

        # if it gets clipped on the previous pass, we need to skip it
        if len(ci.points) != 3 or len(cj.points) != 3:
            return

        if ci.joins[0] == cj.joins[0]:
            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[0], ci.points[1])):

                iri = self._corridor_lmerge_split_long(icor, 0, cj.points[1].clone())
                self._corridor_lmerge_truncate_lshort(jcor, 0, iri)
            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_lshort(icor, 0, iri)
        elif ci.joins[0] == cj.joins[1]:
            if (g.dist2(cj.points[1], cj.points[2]) < g.dist2(ci.points[0], ci.points[1])):
                iri = self._corridor_lmerge_split_long(icor, 0, cj.points[1].clone())
                self._corridor_lmerge_truncate_lshort(jcor, 1, iri)
            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_lshort(icor, 1, iri)

        elif ci.joins[1] == cj.joins[0]:
            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[1], ci.points[2])):
                iri = self._corridor_lmerge_split_long(icor, 1, cj.points[1].clone())
                self._corridor_lmerge_truncate_lshort(jcor, 0, iri)

            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_lshort(icor, 1, iri)

        else:
            assert ci.joins[1] == cj.joins[1]
            if (g.dist2(cj.points[1], cj.points[2]) < g.dist2(ci.points[1], ci.points[2])):
                # lmerge_spur[(1,1)](icor, jcor)
                iri = self._corridor_lmerge_split_long(icor, 1, cj.points[1].clone())
                self._corridor_lmerge_truncate_lshort(jcor, 1, iri)

            else:
                # lmerge_spur[(1,1)](jcor, icor)
                iri = self._corridor_lmerge_split_long(jcor, 1, ci.points[1].clone())
                self._corridor_lmerge_truncate_lshort(icor, 1, iri)


    def _corridor_lmergehv(self, icor, jcor):
        """
        ic is the index of the L corridor
        jc is the index of the horizontal or vertical corridor

                + i2   jc is the shorter.
                |      For this case, c1 remains an L and its i0 foot
        i0+-----+ i1   goes on a new intersection inserted at j1
        j0+--+ j1


                + i2   jc is the longer 
                |      For this case c1 is converted to a straight and
        i0+-----+ i1   the mid point at i1 ends up attached to the new intersection
        j0+-------------+ j1


        """
        ci = self.corridors[icor]
        cj = self.corridors[jcor]

        if len(ci.points) == len(cj.points) and not (len(ci.points) != 2 or len(cj.points) != 2):
            raise ValueError("corridor_lmergehv needs one elbow and one straight")

        if (len(ci.points) != 2 and len(cj.points) != 2):
            raise ValueError("corridor_lmerge two elbows")

        if ci.joins[0] == cj.joins[0]:

            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[0], ci.points[1])):
                # the straight is shorter, so we need to truncate the longer L.
                # cj.points[1] is the point we need to clip the L to.

                # We are going to truncate the L by clipping and attaching it to
                # the room at the other end of cj - as its lying ON the L corridor.
                iri = cj.joins[1] # index of intersection room
                self._corridor_lmerge_truncate_long(icor, 0, cj.points[1].clone(), iri)
                # there is nothing left to do to the shorter straigh corridor.
            else:
                # the straight is longer, so we need to split and create a new intersection
                iri = self._corridor_lmerge_split_hvlong(jcor, 0, ci.points[1].clone())

                # Now convert the L to a straight and attach its old mid point to the intersection
                self._corridor_lmerge_truncate_lshort(icor, 0, iri)
                # now we have the intersection, we can deal with the L by
                # converting it to a straigh and attaching to RI
                # self._corridor_lmerge_truncate_long(icor, 0, ci.points[1].clone(), iri)

        # the remaining cases are the same, its just that the endian-ness of the corridors changes
        elif ci.joins[0] == cj.joins[1]:
            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[0], ci.points[1])):
                iri = cj.joins[0] # index of intersection room
                self._corridor_lmerge_truncate_long(icor, 0, cj.points[0].clone(), iri)
                # self._corridor_lmerge_truncate_long(icor, 0, cj.points[0].clone(), iri)
                # there is nothing left to do to the shorter straigh corridor.
            else:
                # the straight is longer, so we need to split and create a new intersection
                iri = self._corridor_lmerge_split_hvlong(jcor, 1, ci.points[1].clone())

                # Now convert the L to a straight and attach its old mid point to the intersection
                self._corridor_lmerge_truncate_lshort(icor, 0, iri)
                # now we have the intersection, we can deal with the L as above.
                # self._corridor_lmerge_truncate_long(icor, 0, ci.points[1].clone(), iri)

        elif ci.joins[1] == cj.joins[0]:

            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[1], ci.points[2])):
                iri = cj.joins[1] # index of intersection room
                self._corridor_lmerge_truncate_long(icor, 1, cj.points[1].clone(), iri)
                # there is nothing left to do to the shorter straigh corridor.
            else:
                # the straight is longer, so we need to split and create a new intersection
                iri = self._corridor_lmerge_split_hvlong(jcor, 0, ci.points[1].clone())

                # Now convert the L to a straight and attach its old mid point to the intersection
                self._corridor_lmerge_truncate_lshort(icor, 1, iri)
                # now we have the intersection, we can deal with the L as above.
                #self._corridor_lmerge_truncate_long(icor, 1, ci.points[1].clone(), iri)
        else:

            if (g.dist2(cj.points[0], cj.points[1]) < g.dist2(ci.points[1], ci.points[2])):
                iri = cj.joins[0] # index of intersection room
                self._corridor_lmerge_truncate_long(icor, 1, cj.points[0].clone(), iri)
                # there is nothing left to do to the shorter straigh corridor.
            else:
                # the straight is longer, so we need to split and create a new intersection
                iri = self._corridor_lmerge_split_hvlong(jcor, 1, ci.points[1].clone())

                # Now convert the L to a straight and attach its old mid point to the intersection
                self._corridor_lmerge_truncate_lshort(icor, 1, iri)

                # now we have the intersection, we can deal with the L as above.
                # self._corridor_lmerge_truncate_long(icor, 1, ci.points[1].clone(), iri)
    # ---


    def _corridor_lmerge_truncate_long(self, icor, r1end, pi, iri):
        """
        Merge a L with a straight where one end of the straigh lies in the
        middle of the leg of the L
                   R2
                   | ci
        R1 ----+---+ r1end=0
               pi

        """

        ci = self.corridors[icor]

        ir1 = ci.joins[r1end]
        r1 = self.rooms[ir1]
        ri = self.rooms[iri]

        # adjust the corridor join to end at the RI intersection rather than R1
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]

        # we are truncating the leg of the elbow that rests on the common room r1
        ci.points[r1end * 2] = pi.clone()
        # ci.points[r1end] = pi.clone()
        ci.clipped += 1

        # detach the clipped corridor from its orignal r1, and instead attach it
        # to the room associated with the intersection point.  the truncated
        # corrodor direction hasn't changed so the side of the new room entered
        # is the same as before.
        r1side = r1.detach_corridor(icor)
        ri.corridors[r1side].append(icor)

        ci.joins[r1end] = iri
        # join_sides stays the

        print(f"trunc-long: cor: {icor}, ci: {str(orig)} -> {str(ci.joins)}. joins")
        print(f"trunc-long: cor: {icor} ci: {str(orig_sides)} -> {str(ci.join_sides)}. join_sides")


    def _corridor_lmerge_split_hvlong(self, icor, r1end, pi):
        """
        Merge an L with a straight where the straight is longer than the co-incident L leg.


        r1end   ci
        j0+-------------+ j1 R2  icor
    R1  i0+-----+ i1 pi
                .                jcor
                + i2
               R3

            cn  RI(pi) ci
    R1  i0+-----+-------- i1  icor
                . cj L              
                + i2
               R3


        """

        ci = self.corridors[icor]

        p1 = ci.points[r1end].clone()

        ir1 = ci.joins[r1end]
        r1 = self.rooms[ir1]

        # -- create the new corridor segment and the intersection
        cn = Corridor(
            points=[None, None],
            joins=[None, None],
            join_sides=[None, None],
            is_inserted=True
        )

        # note: use r1end directly as cn is a straight with 2 points
        # R1 -- RI
        cn.points[r1end] = p1.clone() # R1
        cn.points[1- r1end] = pi.clone() # RI

        # The new intersection room index
        iri = len(self.rooms)

        # new corridor replaces the r1end of the long straight we are spliting
        cn.joins[r1end] = ci.joins[r1end]
        cn.joins[1 - r1end] = iri

        # as its a straight, the join sides are just a copy
        cn.join_sides[r1end] = ci.join_sides[r1end]
        cn.join_sides[1 - r1end] = ci.join_sides[1 -r1end]

        ri = Room()  # intersection
        ri.is_intersection = True
        ri.center = pi.clone()

        self.corridors.append(cn)
        self.rooms.append(ri)

        # -- detach ci from R1, clip it, then attach to RI
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]

        # detach from R1 and remember which side we were attached to
        r1iside = r1.detach_corridor(icor)

        # clip
        ci.points[r1end] = pi.clone()
        ci.clipped += 1

        # the side of attachment on the new intersection is the same as we attached to on R1
        ri.corridors[r1iside].append(icor)

        ci.joins[r1end] = iri
        # join_sides stays the same
        print(f"split-hvlong: cor: {icor}, ci: {str(orig)} -> {str(ci.joins)}. joins")
        print(f"split-hvlong: cor: {icor} ci: {str(orig_sides)} -> {str(ci.join_sides)}. join_sides")

        # Return new room index so the L can be attached to it
        return iri


    def _corridor_lmerge_split_long(self, icor, r1end, pi):
        """
        Here we are spliting the L between R1 - R2 on the leg joining R1 and inserting a new straight corridor segment
        to join the new intersection to R1

                   R2
            RI(pi) | ci
        R1 --+-----+ r1end=0
             |
               R1 r1end=1
                |
          RI(pi)+--
             ci |
        R2 -----+
        """

        ci = self.corridors[icor]

        # the corridor foot rests on the room attached to the side we are splitting
        ipfoot = r1end * 2 # 0 or 2

        # the corridor head rests on the room attached to the side we are not splitting
        iphead = (1-r1end) * 2 # 0 or 2


        # Make a new corridor joining R1 to the intersection point. The
        # intersection point is the elbow point of the shorter leg of cj.
        ir1 = ci.joins[r1end]
        r1 = self.rooms[ir1]

        # The foot of the new corridor will rest on r1
        p1 = ci.points[ipfoot].clone()

        # create the new corridor segment and the intersection
        cn = Corridor(
            points=[None, None],
            joins=[None, None],
            join_sides=[None, None],
            is_inserted=True
        )

        # note: use r1end directly as cn is a straight with 2 points
        cn.points[r1end] = p1 # R1
        cn.points[1- r1end] = pi # RI

        ri = Room()  # intersection
        ri.is_intersection = True
        ri.center = pi.clone()

        # The new intersection room index
        iri = len(self.rooms)
        ici = len(self.corridors)

        self.corridors.append(cn)
        self.rooms.append(ri)

        # detach ci from room 1 and clip it

        # set the foot of the second leg to the intersection position
        ci.points[ipfoot] = pi.clone()
        ci.clipped += 1 

        # detach ci from room 1
        r1iside = r1.detach_corridor(icor)

        # attach it to the intersection the side of attachment is the *same*
        # side as it was previously attached to R1 on.
        ri.corridors[r1iside].append(icor)

        # update the join for the clipped end so it joins to the new intersection
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]
        assert ci.joins[r1end] == ir1
        ci.joins[r1end] = iri

        print(f"split-long: cor: {icor} ci: {str(ci.joins)} -> {ci.joins}. joins")    

        # make the new corridor segment have the same direction, towards R1, as
        # did ci's leg that we split.

        orig = cn.joins[:] # so we can log before and after
        cn.joins[r1end] = ir1 # R1
        cn.joins[1 - r1end] = iri # intersection
        cn.join_sides[r1end] = r1iside
        cn.join_sides[1 - r1end] = RoomSide.opposite(r1iside)
        r1.corridors[cn.join_sides[r1end]].append(ici)
        ri.corridors[cn.join_sides[1 - r1end]].append(ici)

        print(f"split-long: cor: {icor} cn: {str(orig)} -> {str(cn.joins)}. joins")
        print(f"split-long: cor: {icor} cn: {str(orig_sides)} -> {str(cn.join_sides)}. join_sides")
        print(f"split-long: cor: {icor} cn: {str(r1.corridors)}. r[{ir1}].corridors")
        print(f"split-long: cor: {icor} cn: {str(ri.corridors)}. r[{iri}].corridors")

        return iri


    def _corridor_lmerge_truncate_lshort(self, icor, r1end, iri):
        """
        Deal with the shorter co-incident leg of an entangled L

        Here we are making the L between R1 - R3 into a straight joining R1 R3

        We do this by removing the r1end point. The old elbow point becomes the
        end point. Which is also the center of the new intersection

 r1end=0           
            RI(pi) |
        R1 --+-----+ 
             |  ci
             R3 

               R1 r1end=1
                |     ci
          RI(pi)+----R3 
                |
           -----+
       
        """
        ci = self.corridors[icor]
        r1 = self.rooms[ci.joins[r1end]]
        r3 = self.rooms[ci.joins[1 - r1end]]

        # adjust the corridor join to end at the RI intersection rather than R1
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]

        # we are removing the leg of the elbow that rests on the common room r1
        if r1end == 0:
            ci.points = ci.points[1:]
        else:
            ci.points = ci.points[:2]
        ci.clipped += 1 

        # we want the side *opposite* the side we attach too on R3    
        riside = RoomSide.opposite(ci.join_sides[1-r1end])

        # note: iri is a parameter as it is typically generated by spliting the other entangled 'longer' corridor segment.
        ci.joins[r1end] = iri
        ci.join_sides[r1end] = riside

        print(f"trunc-short: cor: {icor}, ci: {str(orig)} -> {str(ci.joins)}. joins")
        print(f"trunc-short: cor: {icor} ci: {str(orig_sides)} -> {str(ci.join_sides)}. join_sides")

        # detach from R1
        r1.detach_corridor(icor)

        # the re-attachment has to be derived from room 3. we want the opposite of the side icor is attached to.
        riside = RoomSide.opposite(r3.attached_side(icor))
        # attach the truncated corridor to the intersection
        ri = self.rooms[iri]
        ri.corridors[riside].append(icor)
        ir1 = orig[r1end]
        print(f"trunc-short: cor: {icor} cn: {str(r1.corridors)}. r[{ir1}].corridors")
        print(f"trunc-short: cor: {icor} cn: {str(ri.corridors)}. r[{iri}].corridors")