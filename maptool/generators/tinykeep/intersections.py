"""Insert intersections and clip corridors to reconcile partialy co-incident corridors

"""
from collections import namedtuple
from dataclasses import dataclass
from maptool import geometry as g
from maptool.room import Room, RoomSide
from maptool.corridor import Corridor

# cai and cbi are the index into join & join_sides representing R1.
# ica and icb are the corridor indices for ca and cb
Merge = namedtuple("Merge", "cai cbi ica icb cbshort tee".split(), defaults=(None, None, None, None, None, None))

class GenerateIntersections:

    def __init__(self, rooms, corridors):
        self.rooms = rooms
        self.corridors = corridors

    # ---

    def _classify_lhv_merge(self, ica, icb) -> Merge:

        """
        ic is the index of the L corridor
        jc is the index of the horizontal or vertical corridor

                R3
                + i2   jc is the shorter.
            ca  |      For this case, c1 remains an L and its i0 foot
        i0+-----+ i1   goes on a new intersection inserted at j1
     R1 j0+--+ j1
            cb R3
                
            ca
        j0+-------------+ j1 R2
      R1
        i0+-----+ i1   the mid point at i1 ends up attached to the new intersection
            cb  |      For this case c1 is converted to a straight and
                + i2   jc is the longer 
               R3

        """
        ca = self.corridors[ica]
        cb = self.corridors[icb]

        if len(ca.points) + len(cb.points) != 5:
            raise ValueError("_classify_ll_merge needs one L corridor and one straight")

        if len(ca.points) == 3:
            ca, cb = cb, ca
            ica, icb = icb, ica

        cai = cbi = None
        if g.pt_essentially_same(ca.points[0], cb.points[0]):
            cai, cbi = 0, 0
        elif g.pt_essentially_same(ca.points[0], cb.points[-1]):
            cai, cbi = 0, 1
        elif g.pt_essentially_same(ca.points[-1], cb.points[0]):
            cai, cbi = 1, 0
        elif g.pt_essentially_same(ca.points[-1], cb.points[-1]):
            cai, cbi = 1, 1
        else:
            raise ValueError("no co-incident points, corridors are not entanbled")

        cbshort = 0
        if g.pt_dist2(ca.points[cai], ca.points[1-cai]) < g.pt_dist2(cb.points[cbi*2], cb.points[1]):
            cai, cbi = cbi, cai
            ica, icb = icb, ica
            cbshort = 1

        return Merge(cai, cbi, ica, icb, cbshort=cbshort)


    def _classify_ll_merge(self, ica, icb) -> Merge:
        """
                        ^
                        |R2
        R1 +--ca--------.
           +--cb---.
                   | R3
                   `
        ir1  = cb.join[0]
        r1   = rooms[ir1]
        rn.c = cb.points[1]
        irn = len(rooms)
        
        cn.p[0] = cb.points[0]
        cn.p[1] = cb.points[1]
        cn.joins[0] = cb.joins[0]
        cn.joins[1] = irn
        cn.join_sides[0] = cb.join_sides[0]
        cn.join_sides[1] = opposite(cb.join_sides[0])
        
        cb.points  = cb.points[1:3]
        cb.join[0] = irn
        cb.join_sides[0] = opp(cb.join_sides[1])
        rn.corridors[opp(cb.join_sides[1])].append(jcor)

        Merge(cai=0, cbi=0, ...)

                         ^
                         |R2
         R1 +--ca--------.
            <--cb---.
                    | R3
                    +
        Merge(cai=0, cbi=1, ...),

                         +
                         |R2
         R1 <--ca--------.
            +--cb---.
                    | R3
                    `
        Merge(cai=1, cbi=0, ...),

                         +
                         |R2
         R1 <--ca--------.
            <--cb---.
                    | R3
                    +
        Merge(cai=1, cbi=1, ...),

        convergent cases do not require special treatment
        eg
           i0
        R1 o-----ca---------+ 
           o--cb--+         |       
           j0     |R2       | R3
                   `        `
                  rn
        R1 o--cn---+---ca--+
                 cb|R2     | R3
                   `       `
        can be handled identically to the case where R3 is above  R1

        """

        ca = self.corridors[ica]
        cb = self.corridors[icb]

        if len(ca.points) != 3 or len(cb.points) != 3:
            raise ValueError("_classify_ll_merge needs two L corridors")


        cai = cbi = None
        if g.pt_essentially_same(ca.points[0], cb.points[0]):
            cai, cbi = 0, 0
        elif g.pt_essentially_same(ca.points[0], cb.points[-1]):
            cai, cbi = 0, 1
        elif g.pt_essentially_same(ca.points[-1], cb.points[0]):
            cai, cbi = 1, 0
        elif g.pt_essentially_same(ca.points[-1], cb.points[-1]):
            cai, cbi = 1, 1
        else:
            raise ValueError("no co-incident points, corridors are not entanbled")

        tee = 0
        if g.pt_essentially_same(ca.points[1], cb.points[1]):
            tee = 1

        if g.pt_dist2(ca.points[cai*2], ca.points[1]) < g.pt_dist2(cb.points[cbi*2], cb.points[1]):
            cai, cbi = cbi, cai
            ica, icb = icb, ica

        return Merge(cai, cbi, ica, icb, tee=tee)


    def _classify_straight_merge(self, ica, icb) -> Merge:
        """
          +--ca--------> R2
        R1                      R1 cb R3 R2
          +--cb---> R3
        
         r1.detach(ca) -> rdetside
         ca.p[0] = cb.p[1]
         ca.j[0] = cb.j[1]
         r3.attach(ca, opp(rdetside))

        Merge(cai=0, cbi=0, ...)

           +--ca--------> R2
         R1                      R1 cb R3 R2
           <--cb---+ R3
        
          r1.detach(ca) -> rdetside
          ca.p[0] = cb.p[0]
          ca.j[0] = cb.j[0]
          r3.attach(ca, opp(rdetside))
        Merge(cai=0, cbi=1, ...)

           <--ca--------+ R2
         R1                      R1 cb R3 R2
           +--cb---> R3
        
          r1.detach(ca) -> rdetside
          ca.p[0] = cb.p[1]
          ca.j[0] = cb.j[1]
          r3.attach(ca, opp(rdetside))
        Merge(cai=1, cbi=0, ...)

           <--ca--------+ R2
         R1                      R1 cb  R3 ca  R2
           <--cb---+ R3
        
          r1.detach(ca) -> rdetside
          ca.p[1] = cb.p[1]
          ca.j[1] = cb.j[1]
          r3.attach(ca, opp(rdetside))
        Merge(cai=1, cbi=1, ...)
 
        """

        ca = self.corridors[ica]
        cb = self.corridors[icb]

        if len(ca.points) != 2 or len(cb.points) != 2:
            raise ValueError("_classify_straight_merge needs two straight corridors")

        if g.pt_dist2(ca.points[0], ca.points[1]) < g.pt_dist2(cb.points[0], cb.points[1]):
            ca, cb = cb, ca
            ica, icb = icb, ica

        cai = cbi = 1

        if ca.join_sides[0] in [g.LEFT, g.RIGHT]:

            if g.essentially_lt(ca.points[0].x, ca.points[1].x):
                # not inverted, normal is reading order. lower x first
                cai = 0

            if g.essentially_lt(cb.points[0].x, cb.points[1].x):
                # not inverted, normal is reading order. lower x first
                cbi = 0
            return Merge(cai, cbi, ica, icb)

        # lower y is 'north'. north -> south is inverted.
        if g.essentially_lt(ca.points[1].y, ca.points[0].y):
            # second point has lower y, not inverted
            cai = 0
        if g.essentially_lt(cb.points[1].y, cb.points[0].y):
            cbi = 0

        return Merge(cai, cbi, ica, icb)

    def _merge_straights(self, ica, icb):

        m = self._classify_straight_merge(ica, icb)
        ca = self.corridors[m.ica]
        cb = self.corridors[m.icb]

        rd = self.rooms[ca.joins[m.cai]]
        ir3 = cb.joins[1 - m.cbi]
        r3 = self.rooms[ir3]
        rdetside = rd.detach_corridor(m.ica)
        ca.points[m.cai] = cb.points[1 - m.cbi].clone()
        ca.joins[m.cai] = ir3
        #r3.corridors[RoomSide.opposite(rdetside)].append(icor)
        r3.corridors[rdetside].append(m.icb)

    def _merge_ll(self, ica, icb):

        m = self._classify_ll_merge(ica, icb)

        ca = self.corridors[m.ica]
        cb = self.corridors[m.icb]
        ir1 = cb.joins[m.cbi]
        r1 = self.rooms[ir1]

        # --- new room create 
        # new room at the elbow of cb
        rn = Room()  # intersection
        rn.is_intersection = True
        rn.center = cb.points[1]
        irn = len(self.rooms)
        self.rooms.append(rn)

        # --- new corridor
        # new corridor from r1 to rn, replacing the co-incident sections of the entangled pair
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

        # attach the new corridor to r1
        r1.corridors[cn.join_sides[m.cbi]].append(icn)
        # attach the new corridor to rn
        rn.corridors[cn.join_sides[1 - m.cbi]].append(icn)
        # --- new corridor complete

        # --- update ca
        if not m.tee:
            # move first point on ca to the new room
            # truncate the R1 end of ca and attach it to RN
            r1side = r1.detach_corridor(m.ica)

            # note the * 2 gets us to the 'first' point on the corridor independently of its direction
            ca.points[m.cai * 2] = rn.center.clone()
            ca.clipped += 1
            ca.joins[m.cai] = irn
            # join side from R1 is preserved on RN
            rn.corridors[r1side].append(m.ica)
        else:
            # remove the start of ca from R1, convert ca
            # to a straight, attach the remaining leg of ca to RN
            r1.detach_corridor(m.ica)

            ca.joins[m.cai] = irn
            ca.join_sides[m.cai] = RoomSide.opposite(ca.join_sides[1-m.cai])
            ca.points = ca.points[(1-m.cai):2+(1-m.cai)]
            ca.clipped += 1
            rn.corridors[ca.join_sides[m.cai]].append(m.ica)
        # --- ca update complete

        # --- update cb
        # remove the start of cb from R1, convert cb
        # to a straight, attach the remaining leg of cb to RN

        r1.detach_corridor(m.icb)

        cb.joins[m.cbi] = irn
        cb.join_sides[m.cbi] = RoomSide.opposite(cb.join_sides[1-m.cbi])
        cb.points = cb.points[(1-m.cbi):2+(1-m.cbi)]
        cb.clipped += 1

        rn.corridors[cb.join_sides[m.cbi]].append(m.icb)
        # --- cb update complete
        # --- new room complete

    def _merge_lhv(self, ica, icb):

        """
                R3
                + i2   jc is the shorter.
            ca  |      For this case, c1 remains an L and its i0 foot
        i0+-----+ i1   goes on a new intersection inserted at j1
     R1 j0+--+ j1
            cb R3
                
            ca
        j0+-------------+ j1 R2
      R1
        i0+-----+ i1   the mid point at i1 ends up attached to the new intersection
            cb  |      For this case c1 is converted to a straight and
                + i2   jc is the longer 
               R3
        """

        m = self._classify_lhv_merge(ica, icb)
        ca = self.corridors[m.ica]
        cb = self.corridors[m.icb]
        ir1 = cb.joins[m.cbi]
        r1 = self.rooms[ir1]

        if m.cbshort:
            # The horizontal leg is co-incident with an L leg *and* it joins a
            # room that lies on the L this is an odd case that should only
            # result after multiple passes of clipping, which could create an
            # intersection in this way, or if we allow room intersecting
            # corridors at the generation phase.  All we need to do is move the
            # start of the L onto the room. For now, we assume (and assert) that
            # the room is an intersection.

            # --- update cb
            # remove the start of ca from R1 and instead attach it to the end of cb
            ir3 = cb.joins[1 - m.cbi]
            r3 = self.rooms[ir3]

            r1side = r1.detach_corridor(m.ica)
            ca.joins[m.cai] = ir3
            ca.points[m.cai] = r3.center.clone()
            # and attach to r3
            r3.corridors[r1side].append(m.ica)
            return

        # --- new room create 
        # new room at the end of cb
        rn = Room()  # intersection
        rn.is_intersection = True
        rn.center = cb.points[1]
        irn = len(self.rooms)
        self.rooms.append(rn)

        # --- new corridor
        # new corridor from r1 to rn
        cn = Corridor(
            points=[None, None],
            joins=[None, None],
            join_sides=[None, None],
            is_inserted=True
        )

        # ca is the longer straight, cb the short elbow

        # cn is a straight so we don't need to double cbi to get the right index into points
        cn.points[m.cbi] = cb.points[m.cbi * 2].clone() 
        cn.points[1 - m.cbi] = cb.points[1].clone()

        cn.joins[m.cbi] = cb.joins[m.cbi] 
        cn.join_sides[m.cbi] = cb.join_sides[m.cbi]
        cn.joins[1 - m.cbi] = irn
        cn.join_sides[1 - m.cbi] = RoomSide.opposite(cb.join_sides[m.cbi])
        icn = len(self.corridors)

        self.corridors.append(cn)

        # attach the new corridor to r1
        r1.corridors[cn.join_sides[m.cbi]].append(icn)
        # attach the new corridor to rn
        rn.corridors[cn.join_sides[1 - m.cbi]].append(icn)
        # --- new corridor complete

        # --- update ca
        # move first point on ca to the new room
        # truncate the R1 end of ca and attach it to RN
        r1side = r1.detach_corridor(m.ica)

        ca.points[m.cai] = rn.center.clone()
        ca.clipped += 1
        ca.joins[m.cai] = irn
        # join side from R1 is preserved on RN
        rn.corridors[r1side].append(m.ica)
        # --- ca update complete

        # --- update cb
        # remove the start of cb from R1, convert cb
        # to a straight, attach the remaining leg of cb to RN

        r1.detach_corridor(m.icb)

        cb.joins[m.cbi] = irn
        cb.join_sides[m.cbi] = RoomSide.opposite(cb.join_sides[1-m.cbi])
        cb.points = cb.points[(1-m.cbi):2+(1-m.cbi)]
        cb.clipped += 1

        rn.corridors[cb.join_sides[m.cbi]].append(m.icb)
        # --- cb update complete
        # --- new room complete

    # ---
    def snap_close_corridor_pairs(self, margin_factor=0.015):
        """Snap close corridor segments together

        To avoid corridors that are so close to each other that they don't make
        geometric sense (when taking into account the width of the corridro) we
        provide this method to snap them together.

        Two corridors that are snapped will definitely be entangled
        """
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

                        if self.corridors[ic].check_entangled(self.corridors[jc]):
                            continue
                        entangled = self.corridors[ic].check_entangled(self.corridors[jc], margin_factor=margin_factor)
                        if not entangled:
                            continue

                        # ok so the corridor would be entangled if we allow for the margin_factor so snap the co-incident legs together

                        (p1, p2, i, j, opposed) = entangled

                        # are the co-incident legs horizontal or vertical ?
                        ca, cb = self.corridors[ic], self.corridors[jc]
                        if g.essentially_equal(ca.points[i].y, ca.points[i+1].y):
                            # horizontal
                            y = (ca.points[i].y + cb.points[j].y) / 2.0
                            ca.points[i].y = cb.points[j].y = ca.points[i+1].y = cb.points[j+1].y = y
                        else:
                            x = (ca.points[i].x + cb.points[j].x) / 2.0
                            ca.points[i].x = cb.points[j].x = ca.points[i+1].x = cb.points[j+1].x = x
                        if not self.corridors[ic].check_entangled(self.corridors[jc]):
                            raise ValueError('bug')


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

        if len(c1.points) + len(c2.points) == 6:
            self._merge_ll(ic, jc)
            if c1.check_entangled(c2):
                print(f'merge_ll failed to disentangle {ic}, {jc}')
            return True

        if len(c1.points) + len(c2.points) == 5:
            self._merge_lhv(ic, jc)
            if c1.check_entangled(c2):
                print(f'merge_lhv failed to disentangle {ic}, {jc}')

            return True

        if len(c1.points) + len(c2.points) == 4:
            self._merge_straights(ic, jc)
            if c1.check_entangled(c2):
                print(f'merge_straights failed to disentangle {ic}, {jc}')
            return True