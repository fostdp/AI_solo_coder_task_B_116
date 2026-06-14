import math
import numpy as np
from typing import List, Dict, Tuple, Any


class WaterWheelDynamics:
    GRAVITY = 9.81
    WATER_DENSITY = 1000.0

    @classmethod
    def calculate_torque(cls, water_speed: float, blade_angle: float,
                         wheel_radius: float, blade_width: float = 0.3,
                         num_blades: int = 8) -> float:
        theta = math.radians(blade_angle)
        velocity_normal = water_speed * math.sin(theta)
        blade_area = wheel_radius * blade_width
        mass_flow_rate = cls.WATER_DENSITY * velocity_normal * blade_area * 0.7
        force = mass_flow_rate * velocity_normal * 0.85
        torque = force * wheel_radius * math.sin(theta) * num_blades / 4
        return max(torque, 0.0)

    @classmethod
    def calculate_rotational_speed(cls, torque: float, wheel_radius: float,
                                   moment_of_inertia: float = None) -> float:
        if moment_of_inertia is None:
            moment_of_inertia = 0.5 * 500 * wheel_radius ** 2
        if moment_of_inertia <= 0:
            return 0.0
        angular_velocity = (torque * 60) / (2 * math.pi * moment_of_inertia) * 0.3
        return abs(angular_velocity)

    @classmethod
    def calculate_power(cls, torque: float, rotational_speed: float) -> float:
        omega = rotational_speed * 2 * math.pi / 60
        power = torque * omega
        return power


class TransmissionSystem:
    BASE_SLIP_RATE = 0.02
    PULLEY_RADIUS_DRIVER = 0.3
    PULLEY_RADIUS_DRIVEN = 0.15

    @classmethod
    def calculate_critical_torque(cls, belt_friction_coeff: float,
                                  wrap_angle: float = math.pi,
                                  initial_tension: float = 200.0,
                                  pulley_radius: float = 0.15) -> float:
        if belt_friction_coeff <= 0 or wrap_angle <= 0:
            return float('inf')
        e_mu_alpha = math.exp(belt_friction_coeff * wrap_angle)
        max_force_diff = 2 * initial_tension * (e_mu_alpha - 1) / (e_mu_alpha + 1)
        critical_torque = max_force_diff * pulley_radius
        return max(critical_torque, 1.0)

    @classmethod
    def calculate_slip_rate(cls, required_torque: float, critical_torque: float,
                            base_slip: float = 0.02) -> float:
        if critical_torque <= 0:
            return 1.0
        if required_torque <= critical_torque:
            elastic_slip = base_slip * (required_torque / critical_torque)
            return base_slip * 0.3 + elastic_slip * 0.7
        else:
            severe_slip = 1.0 - critical_torque / required_torque
            return min(0.08 + severe_slip * 0.9, 0.95)

    @classmethod
    def calculate_output_torque(cls, input_torque: float, gear_ratio: float,
                                mechanical_efficiency: float,
                                belt_friction_coeff: float = 0.35,
                                wrap_angle: float = math.pi,
                                initial_tension: float = 200.0,
                                driven_pulley_radius: float = 0.15) -> Tuple[float, float, float]:
        critical_torque = cls.calculate_critical_torque(
            belt_friction_coeff, wrap_angle, initial_tension, driven_pulley_radius
        )

        theoretical_torque = input_torque * gear_ratio

        if theoretical_torque <= critical_torque:
            effective_torque = theoretical_torque * mechanical_efficiency
        else:
            effective_torque = critical_torque * mechanical_efficiency

        slip_rate = cls.calculate_slip_rate(theoretical_torque, critical_torque)
        return effective_torque, slip_rate, critical_torque

    @classmethod
    def calculate_output_speed(cls, input_speed: float, gear_ratio: float,
                               slip_rate: float) -> float:
        return input_speed * gear_ratio * max(1.0 - slip_rate, 0.0)

    @classmethod
    def calculate_power_loss(cls, input_power: float, mechanical_efficiency: float,
                             slip_rate: float) -> float:
        slip_loss = input_power * slip_rate * 0.5
        friction_loss = input_power * (1 - mechanical_efficiency)
        return slip_loss + friction_loss


class SpindleDynamics:
    FRICTION_BASE = 0.05
    AIR_RESISTANCE_COEFF = 0.001

    @classmethod
    def calculate_friction_torque(cls, speed: float, friction_coefficient: float = 0.1) -> float:
        viscous_friction = friction_coefficient * speed
        coulomb_friction = cls.FRICTION_BASE * (1 if speed > 0 else 0)
        air_resistance = cls.AIR_RESISTANCE_COEFF * speed ** 2
        return viscous_friction + coulomb_friction + air_resistance

    @classmethod
    def calculate_speed_fluctuation(cls, base_speed: float, spindle_id: int,
                                    num_spindles: int) -> float:
        fluctuation_magnitude = base_speed * 0.02
        phase = (spindle_id / num_spindles) * 2 * math.pi
        speed = base_speed + fluctuation_magnitude * math.sin(phase)
        mechanical_noise = np.random.normal(0, base_speed * 0.005)
        return speed + mechanical_noise

    @classmethod
    def calculate_tension(cls, speed: float, yarn_density: float = 0.001) -> float:
        base_tension = 5.0
        centripetal_tension = yarn_density * speed ** 2 * 0.1
        return base_tension + centripetal_tension

    @classmethod
    def calculate_twist(cls, speed: float, delivery_rate: float = 0.5) -> float:
        if delivery_rate <= 0:
            return 0.0
        twist_per_minute = speed
        twist_per_meter = twist_per_minute / (delivery_rate * 60)
        return twist_per_meter

    @classmethod
    def calculate_breakage_probability(cls, tension: float, max_tension: float = 15.0) -> float:
        if tension <= 0:
            return 0.0
        ratio = tension / max_tension
        breakage_prob = 0.01 * math.exp(3 * (ratio - 0.8)) if ratio > 0.8 else 0.001
        return min(breakage_prob, 1.0)


class TwistUniformityAnalyzer:
    @classmethod
    def calculate_twist_variance(cls, twists: List[float]) -> float:
        if len(twists) < 2:
            return 0.0
        return float(np.var(twists))

    @classmethod
    def calculate_twist_mean(cls, twists: List[float]) -> float:
        if not twists:
            return 0.0
        return float(np.mean(twists))

    @classmethod
    def calculate_coefficient_of_variation(cls, twists: List[float]) -> float:
        mean = cls.calculate_twist_mean(twists)
        if mean == 0:
            return 0.0
        variance = cls.calculate_twist_variance(twists)
        std_dev = math.sqrt(variance)
        return (std_dev / mean) * 100

    @classmethod
    def calculate_speed_standard_deviation(cls, speeds: List[float]) -> float:
        if len(speeds) < 2:
            return 0.0
        return float(np.std(speeds))


class SpinningWheelSimulator:
    def __init__(self):
        self.water_wheel = WaterWheelDynamics()
        self.transmission = TransmissionSystem()
        self.spindle = SpindleDynamics()
        self.analyzer = TwistUniformityAnalyzer()

    def simulate(self, water_speed: float, blade_angle: float,
                 wheel_radius: float, gear_ratio: float,
                 mechanical_efficiency: float, num_spindles: int,
                 friction_coefficient: float = 0.1,
                 belt_friction_coeff: float = 0.35,
                 wrap_angle: float = math.pi,
                 initial_belt_tension: float = 200.0) -> Dict[str, Any]:
        wheel_torque = self.water_wheel.calculate_torque(water_speed, blade_angle, wheel_radius)
        wheel_speed = self.water_wheel.calculate_rotational_speed(wheel_torque, wheel_radius)

        output_torque, slip_rate, critical_torque = self.transmission.calculate_output_torque(
            input_torque=wheel_torque,
            gear_ratio=gear_ratio,
            mechanical_efficiency=mechanical_efficiency,
            belt_friction_coeff=belt_friction_coeff,
            wrap_angle=wrap_angle,
            initial_tension=initial_belt_tension
        )
        output_speed = self.transmission.calculate_output_speed(wheel_speed, gear_ratio, slip_rate)

        spindles = []
        speeds = []
        twists = []
        total_production = 0.0
        broken_count = 0

        torque_per_spindle = output_torque / num_spindles if num_spindles > 0 else 0

        for i in range(num_spindles):
            base_speed = output_speed * 0.95
            actual_speed = self.spindle.calculate_speed_fluctuation(base_speed, i, num_spindles)

            friction_torque = self.spindle.calculate_friction_torque(actual_speed, friction_coefficient)
            net_torque = torque_per_spindle - friction_torque
            if net_torque < 0:
                actual_speed = actual_speed * 0.8

            tension = self.spindle.calculate_tension(actual_speed)
            twist = self.spindle.calculate_twist(actual_speed)

            breakage_prob = self.spindle.calculate_breakage_probability(tension)
            broken = np.random.random() < breakage_prob

            if broken:
                broken_count += 1
                actual_speed = 0
                twist = 0

            delivery_rate = actual_speed * 0.01
            if not broken:
                total_production += delivery_rate

            spindles.append({
                "spindle_id": i,
                "speed": actual_speed,
                "tension": tension,
                "twist": twist,
                "broken": broken
            })
            speeds.append(actual_speed)
            twists.append(twist)

        twist_variance = self.analyzer.calculate_twist_variance(twists)
        twist_cv = self.analyzer.calculate_coefficient_of_variation(twists)
        speed_std = self.analyzer.calculate_speed_standard_deviation(speeds)
        breakage_rate = (broken_count / num_spindles) * 100 if num_spindles > 0 else 0

        input_power = self.water_wheel.calculate_power(wheel_torque, wheel_speed) / 1000
        energy_efficiency = total_production / input_power if input_power > 0 else 0

        return {
            "water_wheel": {
                "water_speed": water_speed,
                "blade_angle": blade_angle,
                "wheel_radius": wheel_radius,
                "torque": wheel_torque,
                "rotational_speed": wheel_speed
            },
            "transmission": {
                "gear_ratio": gear_ratio,
                "mechanical_efficiency": mechanical_efficiency,
                "input_torque": wheel_torque,
                "output_torque": output_torque,
                "input_speed": wheel_speed,
                "output_speed": output_speed,
                "slip_rate": slip_rate,
                "critical_torque": critical_torque,
                "belt_friction_coeff": belt_friction_coeff,
                "wrap_angle_deg": math.degrees(wrap_angle)
            },
            "spindles": spindles,
            "total_production_rate": total_production,
            "energy_efficiency": energy_efficiency,
            "twist_uniformity_cv": twist_cv,
            "breakage_rate": breakage_rate,
            "twist_variance": twist_variance,
            "speed_standard_deviation": speed_std
        }


simulator = SpinningWheelSimulator()
