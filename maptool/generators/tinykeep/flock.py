"""flocking implementation for spreading out rooms"""
import sys
import math
import random
from dataclasses import dataclass

from maptool.geometry import essentially_zero


@dataclass
class Boid:
    """
    see: https://github.com/sowmya214/boids_implementation
    """

    def __init__(self, room):
        self.room = room
        self.center = room.center
        self.angle = random.uniform(0.0, 2.0 * math.pi)

    def euclidean_dist(self, other):
        return self.room.euclidean_dist(other.room)

    def separation(self, nearest, min_separation, tan_fudge=0.0001):
        """move 1: move away from nearest - separation"""
        if nearest is None:
            return
        if self.euclidean_dist(nearest) >= min_separation:
            return

        if essentially_zero(nearest.room.center.x - self.center.x):
            delta = math.atan((nearest.center.y - self.center.y) / tan_fudge)
        else:
            delta = math.atan(
                (nearest.center.y - self.center.y) / (nearest.center.x - self.center.x)
            )
        self.angle -= delta

    def flock(self, distance=10.0):
        try:
            dx, dy = distance * math.cos(self.angle), distance * math.sin(self.angle)
            self.center.x += dx
            self.center.y += dy
        except ValueError:
            print(f"angle: {self.angle}")


def alignment(boid, neighbours, rate=100.0):
    """move 2: orient towards the neighbours - alignment"""

    avg_angle = 0.0

    if not neighbours:
        return

    for n in neighbours:
        avg_angle += n.angle

    avg_angle /= len(neighbours)

    boid.angle -= (avg_angle - boid.angle) / rate
    boid.angle = avg_angle


def cohesion(boid, neighbours, tan_fudge=0.0001, rate=20.0):
    """move 3: move together cohesion"""

    if not neighbours:
        return

    avg_x = 0.0
    avg_y = 0.0

    for n in neighbours:
        avg_x += n.center.x
        avg_y += n.center.y

    avg_x /= len(neighbours)
    avg_y /= len(neighbours)

    if avg_x - boid.center.x < sys.float_info.epsilon * 2:
        angle = math.atan((avg_y - boid.center.y) / tan_fudge)
    else:
        angle = math.atan((avg_y - boid.center.y) / (avg_x - boid.center.x))

    boid.angle -= angle / rate
