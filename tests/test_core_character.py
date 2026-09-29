import unittest
from calypso.character.controller import CharacterController

class CharacterCoreTests(unittest.TestCase):
    def test_four_direction_selection(self):
        character = CharacterController((0, 0), speed=10)
        for target, direction in [((10, 0), "right"), ((0, 10), "down"), ((-10, 0), "left"), ((0, -10), "up")]:
            character.position = (0, 0)
            character.follow(target, 0.1)
            self.assertEqual(character.direction, direction)

    def test_one_second_consumes_multiple_segments(self):
        character = CharacterController((0, 0), speed=10)
        character.set_path([(3, 0), (6, 0), (9, 0)])
        self.assertTrue(character.tick(1.0))
        self.assertEqual(character.position, (9.0, 0.0))

    def test_run_speed(self):
        character = CharacterController((0, 0), speed=10, run_speed=30)
        character.running = True
        character.tick(1.0)
        character.set_path([(100, 0)])
        character.tick(1.0)
        self.assertEqual(character.position, (30.0, 0.0))

    def test_duplicate_waypoints_and_arrival(self):
        character = CharacterController((0, 0), speed=10)
        character.set_path([(0, 0), (5, 0), (5, 0), (5, 5)])
        self.assertEqual(character.path, [(5.0, 0.0), (5.0, 5.0)])
        self.assertFalse(character.tick(.5))
        self.assertEqual(character.direction, "right")
        self.assertTrue(character.tick(.5))
        self.assertEqual(character.direction, "down")
        self.assertEqual(character.position, (5.0, 5.0))
        self.assertEqual(character.path, [])

    def test_delta_time_and_interrupt_replan(self):
        once = CharacterController((0, 0), speed=10)
        many = CharacterController((0, 0), speed=10)
        for character in (once, many):
            character.set_path([(10, 10)])
        once.tick(1)
        for _ in range(10):
            many.tick(.1)
        self.assertAlmostEqual(once.position[0], many.position[0])
        self.assertAlmostEqual(once.position[1], many.position[1])
        many.set_path([(0, 0)])
        many.tick(.1)
        self.assertEqual(many.direction, "left")

if __name__ == "__main__":
    unittest.main()
