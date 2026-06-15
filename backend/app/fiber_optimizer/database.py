"""
棉麻丝纤维特性与纺纱参数优化模块
基于不同纤维的物理特性，智能调整牵伸倍数、加捻参数等工艺参数
"""
from __future__ import annotations

from typing import Dict, Optional

from .models import FiberProperties


class FiberDatabase:
    """纤维特性数据库"""

    @staticmethod
    def get_all_fibers() -> Dict[str, FiberProperties]:
        """获取所有纤维特性"""
        return {
            "cotton": FiberProperties(
                fiber_type="cotton",
                fiber_name="棉花",
                scientific_name="Gossypium",
                origin="植物种子纤维",
                color="本白/乳白",
                fiber_length_mm_avg=28.0,
                fiber_length_mm_min=22.0,
                fiber_length_mm_max=38.0,
                fiber_diameter_um=16.0,
                fineness_dtex=1.6,
                density_g_cm3=1.54,
                breaking_tenacity_cn_dtex=2.8,
                elongation_at_break_percent=7.0,
                moisture_regain_percent=8.5,
                modulus_gpa=8.5,
                friction_coefficient=0.28,
                crimp_percent=5.0,
                typical_count_tex_range=(30.0, 400.0),
                recommended_twist_factor_range=(320.0, 420.0),
                recommended_draft_range=(15.0, 40.0),
                max_spindle_speed_rpm=450.0,
                description="最常见的纺织纤维，柔软舒适，吸湿性好，适合织造各类服装面料和家纺产品。"
            ),
            "hemp": FiberProperties(
                fiber_type="hemp",
                fiber_name="苎麻",
                scientific_name="Boehmeria nivea",
                origin="植物韧皮纤维",
                color="本白/黄白",
                fiber_length_mm_avg=60.0,
                fiber_length_mm_min=40.0,
                fiber_length_mm_max=120.0,
                fiber_diameter_um=30.0,
                fineness_dtex=6.5,
                density_g_cm3=1.50,
                breaking_tenacity_cn_dtex=4.2,
                elongation_at_break_percent=3.5,
                moisture_regain_percent=12.0,
                modulus_gpa=22.0,
                friction_coefficient=0.35,
                crimp_percent=1.0,
                typical_count_tex_range=(100.0, 600.0),
                recommended_twist_factor_range=(280.0, 380.0),
                recommended_draft_range=(8.0, 20.0),
                max_spindle_speed_rpm=350.0,
                description="中国传统特色纤维，强度高，凉爽透气，抗菌防霉，适合夏季服装和高档家纺。"
            ),
            "flax": FiberProperties(
                fiber_type="flax",
                fiber_name="亚麻",
                scientific_name="Linum usitatissimum",
                origin="植物韧皮纤维",
                color="本白/浅黄",
                fiber_length_mm_avg=50.0,
                fiber_length_mm_min=30.0,
                fiber_length_mm_max=90.0,
                fiber_diameter_um=22.0,
                fineness_dtex=3.8,
                density_g_cm3=1.49,
                breaking_tenacity_cn_dtex=3.8,
                elongation_at_break_percent=3.0,
                moisture_regain_percent=10.0,
                modulus_gpa=18.0,
                friction_coefficient=0.33,
                crimp_percent=1.5,
                typical_count_tex_range=(80.0, 500.0),
                recommended_twist_factor_range=(260.0, 360.0),
                recommended_draft_range=(10.0, 22.0),
                max_spindle_speed_rpm=380.0,
                description="欧洲传统高档纤维，光泽优雅，吸湿透气，挺括有型，适合高端服装面料。"
            ),
            "silk": FiberProperties(
                fiber_type="silk",
                fiber_name="桑蚕丝",
                scientific_name="Bombyx mori",
                origin="动物蛋白纤维",
                color="珍珠白/乳黄",
                fiber_length_mm_avg=1200.0,
                fiber_length_mm_min=800.0,
                fiber_length_mm_max=1500.0,
                fiber_diameter_um=12.0,
                fineness_dtex=3.0,
                density_g_cm3=1.34,
                breaking_tenacity_cn_dtex=3.8,
                elongation_at_break_percent=20.0,
                moisture_regain_percent=11.0,
                modulus_gpa=10.0,
                friction_coefficient=0.22,
                crimp_percent=0.0,
                typical_count_tex_range=(10.0, 200.0),
                recommended_twist_factor_range=(350.0, 480.0),
                recommended_draft_range=(1.5, 5.0),
                max_spindle_speed_rpm=500.0,
                description="纤维皇后，光泽华贵，触感柔滑，穿着舒适，自古以来就是高档纺织品的首选原料。"
            ),
            "wool": FiberProperties(
                fiber_type="wool",
                fiber_name="绵羊毛",
                scientific_name="Ovis aries",
                origin="动物蛋白纤维",
                color="本白/米白",
                fiber_length_mm_avg=80.0,
                fiber_length_mm_min=50.0,
                fiber_length_mm_max=150.0,
                fiber_diameter_um=25.0,
                fineness_dtex=4.0,
                density_g_cm3=1.31,
                breaking_tenacity_cn_dtex=1.8,
                elongation_at_break_percent=35.0,
                moisture_regain_percent=15.0,
                modulus_gpa=3.5,
                friction_coefficient=0.30,
                crimp_percent=25.0,
                typical_count_tex_range=(50.0, 400.0),
                recommended_twist_factor_range=(300.0, 400.0),
                recommended_draft_range=(12.0, 28.0),
                max_spindle_speed_rpm=400.0,
                description="天然保暖纤维，弹性好，吸湿排汗，是毛纺和针织产品的主要原料。"
            )
        }

    @staticmethod
    def get_fiber(fiber_type: str) -> Optional[FiberProperties]:
        """获取指定纤维特性"""
        fibers = FiberDatabase.get_all_fibers()
        return fibers.get(fiber_type)
