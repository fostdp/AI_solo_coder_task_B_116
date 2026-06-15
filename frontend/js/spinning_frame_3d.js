/**
 * spinning_frame_3d.js — 纯三维渲染模块
 * 职责:
 *   - 创建机架、水轮、主轴、32锭(InstancedMesh)、纱线几何
 *   - 每帧更新旋转动画、实例矩阵、纱线波形
 *   - 提供射线拾取需要的 getClickableObjects / getSpindleInfo
 * 不负责:
 *   - 面板 DOM 交互 (→ efficiency_panel.js)
 *   - API 请求与图表绘制 (→ efficiency_panel.js)
 */
class SpinningFrame3D {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.spindleCount = 32;
        this.instancedSpindleParts = [];
        this.spindlePartGeometries = [];
        this.spindleRotationSpeeds = [];
        this.spindlePositions = [];
        this.yarns = [];
        this.wheelGroup = null;
        this.mainShaft = null;
        this.showYarn = true;
        this.wheelRotation = 0;
        this.spindleRotationAccum = new Float32Array(this.spindleCount);
        this.time = 0;
        this.yarnUpdateCounter = 0;
        this.yarnUpdateInterval = 3;

        this.createFrame();
        this.createWaterWheel();
        this.createMainShaft();
        this.createSpindlesInstanced();
        this.createYarns();

        this.scene.add(this.group);
    }

    createFrame() {
        const frameGroup = new THREE.Group();
        frameGroup.userData = {
            type: 'frame',
            name: '机架',
            description: '水转大纺车的木质机架，采用榫卯结构，支撑整个纺车系统。',
            material: '硬木（楠木、枣木）',
            height: '约2.5米',
            weight: '约500公斤'
        };

        const woodMaterial = new THREE.MeshStandardMaterial({
            color: 0x8B4513,
            roughness: 0.8,
            metalness: 0.2
        });

        const darkWoodMaterial = new THREE.MeshStandardMaterial({
            color: 0x654321,
            roughness: 0.85,
            metalness: 0.15
        });

        const legGeometry = new THREE.BoxGeometry(0.3, 5, 0.3);
        const legPositions = [
            { x: -4, z: -2 },
            { x: 4, z: -2 },
            { x: -4, z: 2 },
            { x: 4, z: 2 }
        ];

        legPositions.forEach(pos => {
            const leg = new THREE.Mesh(legGeometry, darkWoodMaterial);
            leg.position.set(pos.x, 2.5, pos.z);
            leg.castShadow = true;
            leg.receiveShadow = true;
            frameGroup.add(leg);
        });

        const beamGeometry1 = new THREE.BoxGeometry(8.6, 0.3, 0.3);
        const topBeam1 = new THREE.Mesh(beamGeometry1, woodMaterial);
        topBeam1.position.set(0, 5, -2);
        topBeam1.castShadow = true;
        frameGroup.add(topBeam1);

        const topBeam2 = new THREE.Mesh(beamGeometry1, woodMaterial);
        topBeam2.position.set(0, 5, 2);
        topBeam2.castShadow = true;
        frameGroup.add(topBeam2);

        const beamGeometry2 = new THREE.BoxGeometry(0.3, 0.3, 4.6);
        const sideBeam1 = new THREE.Mesh(beamGeometry2, woodMaterial);
        sideBeam1.position.set(-4, 5, 0);
        sideBeam1.castShadow = true;
        frameGroup.add(sideBeam1);

        const sideBeam2 = new THREE.Mesh(beamGeometry2, woodMaterial);
        sideBeam2.position.set(4, 5, 0);
        sideBeam2.castShadow = true;
        frameGroup.add(sideBeam2);

        const midBeamGeometry = new THREE.BoxGeometry(8.6, 0.2, 0.2);
        const midBeam1 = new THREE.Mesh(midBeamGeometry, darkWoodMaterial);
        midBeam1.position.set(0, 2.5, -2);
        midBeam1.castShadow = true;
        frameGroup.add(midBeam1);

        const midBeam2 = new THREE.Mesh(midBeamGeometry, darkWoodMaterial);
        midBeam2.position.set(0, 2.5, 2);
        midBeam2.castShadow = true;
        frameGroup.add(midBeam2);

        const diagonalGeometry = new THREE.CylinderGeometry(0.08, 0.08, 3.5, 8);
        const diagonal1 = new THREE.Mesh(diagonalGeometry, darkWoodMaterial);
        diagonal1.position.set(-2, 3.7, -2);
        diagonal1.rotation.z = Math.PI / 6;
        diagonal1.castShadow = true;
        frameGroup.add(diagonal1);

        const diagonal2 = new THREE.Mesh(diagonalGeometry, darkWoodMaterial);
        diagonal2.position.set(2, 3.7, -2);
        diagonal2.rotation.z = -Math.PI / 6;
        diagonal2.castShadow = true;
        frameGroup.add(diagonal2);

        this.frameGroup = frameGroup;
        this.group.add(frameGroup);
    }

    createWaterWheel() {
        this.wheelGroup = new THREE.Group();
        this.wheelGroup.userData = {
            type: 'waterWheel',
            name: '水轮',
            description: '水转大纺车的动力来源，水流冲击叶片带动水轮旋转，通过皮带传动驱动锭子转动。打滑率由欧拉皮带公式计算。',
            diameter: '约3米',
            bladeCount: '24片',
            material: '木质框架 + 竹制叶片',
            transmission: '皮带传动（含打滑修正）'
        };

        const woodMaterial = new THREE.MeshStandardMaterial({
            color: 0x8B4513,
            roughness: 0.75,
            metalness: 0.1
        });

        const bambooMaterial = new THREE.MeshStandardMaterial({
            color: 0xDAA520,
            roughness: 0.6,
            metalness: 0.1
        });

        const hubGeometry = new THREE.CylinderGeometry(0.4, 0.4, 1.5, 16);
        const hub = new THREE.Mesh(hubGeometry, woodMaterial);
        hub.rotation.z = Math.PI / 2;
        hub.castShadow = true;
        this.wheelGroup.add(hub);

        const wheelRadius = 3;
        const rimGeometry = new THREE.TorusGeometry(wheelRadius, 0.15, 8, 32);
        const rim = new THREE.Mesh(rimGeometry, woodMaterial);
        rim.rotation.y = Math.PI / 2;
        rim.castShadow = true;
        this.wheelGroup.add(rim);

        const rim2 = new THREE.Mesh(rimGeometry, woodMaterial);
        rim2.rotation.y = Math.PI / 2;
        rim2.position.z = 1.2;
        rim2.castShadow = true;
        this.wheelGroup.add(rim2);

        const spokeCount = 12;
        const spokeGeometry = new THREE.BoxGeometry(0.1, wheelRadius - 0.4, 0.1);

        for (let i = 0; i < spokeCount; i++) {
            const angle = (i / spokeCount) * Math.PI * 2;

            const spoke1 = new THREE.Mesh(spokeGeometry, woodMaterial);
            spoke1.position.y = (wheelRadius - 0.4) / 2;
            spoke1.position.z = -0.6;
            spoke1.rotation.z = -angle;
            spoke1.castShadow = true;
            this.wheelGroup.add(spoke1);

            const spoke2 = new THREE.Mesh(spokeGeometry, woodMaterial);
            spoke2.position.y = (wheelRadius - 0.4) / 2;
            spoke2.position.z = 0.6;
            spoke2.rotation.z = -angle;
            spoke2.castShadow = true;
            this.wheelGroup.add(spoke2);
        }

        const bladeCount = 24;
        const bladeWidth = 0.6;
        const bladeHeight = 0.8;

        for (let i = 0; i < bladeCount; i++) {
            const angle = (i / bladeCount) * Math.PI * 2;
            const bladeGeometry = new THREE.BoxGeometry(bladeWidth, bladeHeight, 0.08);
            const blade = new THREE.Mesh(bladeGeometry, bambooMaterial);

            blade.position.x = Math.cos(angle) * wheelRadius;
            blade.position.y = Math.sin(angle) * wheelRadius;
            blade.rotation.z = angle + Math.PI / 2;
            blade.castShadow = true;

            this.wheelGroup.add(blade);
        }

        const gearGeometry = new THREE.CylinderGeometry(0.8, 0.8, 0.3, 32);
        const gear = new THREE.Mesh(gearGeometry, woodMaterial);
        gear.position.z = 1.2;
        gear.castShadow = true;
        this.wheelGroup.add(gear);

        for (let i = 0; i < 16; i++) {
            const angle = (i / 16) * Math.PI * 2;
            const toothGeometry = new THREE.BoxGeometry(0.15, 0.2, 0.3);
            const tooth = new THREE.Mesh(toothGeometry, woodMaterial);
            tooth.position.x = Math.cos(angle) * 0.85;
            tooth.position.y = Math.sin(angle) * 0.85;
            tooth.position.z = 1.2;
            tooth.rotation.z = angle;
            tooth.castShadow = true;
            this.wheelGroup.add(tooth);
        }

        this.wheelGroup.position.set(-8, 4, 0);
        this.group.add(this.wheelGroup);
    }

    createMainShaft() {
        const shaftGroup = new THREE.Group();
        shaftGroup.userData = {
            type: 'mainShaft',
            name: '主轴',
            description: '连接水轮和锭子的传动主轴，将水轮的旋转动力通过皮带传动分配给32个锭子。打滑率由欧拉公式动态计算。',
            length: '约8米',
            diameter: '约20厘米',
            material: '硬木 + 铁轴套',
            transmissionRatio: '1:3.5（含打滑修正）'
        };

        const woodMaterial = new THREE.MeshStandardMaterial({
            color: 0x654321,
            roughness: 0.7,
            metalness: 0.2
        });

        const ironMaterial = new THREE.MeshStandardMaterial({
            color: 0x696969,
            roughness: 0.4,
            metalness: 0.8
        });

        const shaftGeometry = new THREE.CylinderGeometry(0.12, 0.12, 10, 16);
        const shaft = new THREE.Mesh(shaftGeometry, woodMaterial);
        shaft.rotation.z = Math.PI / 2;
        shaft.castShadow = true;
        shaftGroup.add(shaft);

        const ringGeometry = new THREE.TorusGeometry(0.15, 0.03, 8, 16);
        for (let i = 0; i < 8; i++) {
            const ring = new THREE.Mesh(ringGeometry, ironMaterial);
            ring.rotation.y = Math.PI / 2;
            ring.position.x = -4 + i * 1.2;
            ring.castShadow = true;
            shaftGroup.add(ring);
        }

        const driveGearGeometry = new THREE.CylinderGeometry(0.6, 0.6, 0.25, 32);
        const driveGear = new THREE.Mesh(driveGearGeometry, woodMaterial);
        driveGear.position.x = -5;
        driveGear.rotation.x = Math.PI / 2;
        driveGear.castShadow = true;
        shaftGroup.add(driveGear);

        for (let i = 0; i < 12; i++) {
            const angle = (i / 12) * Math.PI * 2;
            const toothGeometry = new THREE.BoxGeometry(0.12, 0.15, 0.25);
            const tooth = new THREE.Mesh(toothGeometry, woodMaterial);
            tooth.position.x = -5;
            tooth.position.y = Math.cos(angle) * 0.65;
            tooth.position.z = Math.sin(angle) * 0.65;
            tooth.rotation.y = angle;
            tooth.castShadow = true;
            shaftGroup.add(tooth);
        }

        this.mainShaft = shaftGroup;
        this.mainShaft.position.set(0, 4.8, 0);
        this.group.add(this.mainShaft);
    }

    _makeSpindlePart(name, geometry, material) {
        this.spindlePartGeometries.push({ name, geometry });
        return geometry;
    }

    createSpindlesInstanced() {
        const rows = 2;
        const cols = 16;
        const spacing = 0.9;

        const spindleMaterial = new THREE.MeshStandardMaterial({
            color: 0xDAA520,
            roughness: 0.6,
            metalness: 0.2
        });

        const baseMaterial = new THREE.MeshStandardMaterial({
            color: 0x8B4513,
            roughness: 0.8,
            metalness: 0.1
        });

        const bobbinMaterial = new THREE.MeshStandardMaterial({
            color: 0xf5deb3,
            roughness: 0.9,
            metalness: 0
        });

        const partSpecs = [
            { name: 'base',   geometry: new THREE.CylinderGeometry(0.15, 0.18, 0.3, 12), material: baseMaterial,  yOffset: 0.15 },
            { name: 'shaft',  geometry: new THREE.CylinderGeometry(0.04, 0.04, 0.6, 8),   material: spindleMaterial, yOffset: 0.6 },
            { name: 'whorl',  geometry: new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16), material: spindleMaterial, yOffset: 0.4 },
            { name: 'tip',    geometry: new THREE.ConeGeometry(0.04, 0.15, 8),           material: spindleMaterial, yOffset: 0.97 },
            { name: 'bobbin', geometry: new THREE.CylinderGeometry(0.08, 0.08, 0.3, 12), material: bobbinMaterial,  yOffset: 0.65 }
        ];

        this.spindleGroup = new THREE.Group();
        this.instancedSpindleParts = [];
        this.spindlePositions = [];
        this.spindleBaseRotationSpeeds = [];

        const dummy = new THREE.Object3D();
        const partNames = [];

        partSpecs.forEach((spec, partIdx) => {
            const instanced = new THREE.InstancedMesh(spec.geometry, spec.material, this.spindleCount);
            instanced.castShadow = true;
            instanced.userData = {
                type: 'spindlePart',
                partName: spec.name,
                partYOffset: spec.yOffset,
                isSpindleInstanced: true
            };
            instanced.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
            this.instancedSpindleParts.push(instanced);
            this.spindleGroup.add(instanced);
            partNames.push(spec.name);
        });

        this.spindlePartNames = partNames;

        let spindleIdx = 0;
        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const x = -((cols - 1) / 2) * spacing + col * spacing;
                const z = row === 0 ? -1.5 : 1.5;
                const y = 2.5;

                this.spindlePositions.push({ x, y, z, index: spindleIdx });

                const baseSpeed = 0.8 + Math.random() * 0.4;
                this.spindleBaseRotationSpeeds.push(baseSpeed);
                this.spindleRotationAccum[spindleIdx] = Math.random() * Math.PI * 2;

                partSpecs.forEach((spec, partIdx) => {
                    dummy.position.set(x, y + spec.yOffset, z);
                    dummy.rotation.set(0, this.spindleRotationAccum[spindleIdx], 0);
                    dummy.scale.set(1, 1, 1);
                    dummy.updateMatrix();
                    this.instancedSpindleParts[partIdx].setMatrixAt(spindleIdx, dummy.matrix);
                });

                spindleIdx++;
            }
        }

        this.instancedSpindleParts.forEach(inst => inst.instanceMatrix.needsUpdate = true);

        this.spindleGroup.userData = {
            type: 'spindleGroup',
            name: '锭子阵列（32锭）',
            description: '使用InstancedMesh实例化渲染，draw call从160降至5，显著提升移动端帧率。'
        };

        this.group.add(this.spindleGroup);
    }

    getSpindleInfo(instanceId) {
        if (instanceId < 0 || instanceId >= this.spindleCount) return null;
        const pos = this.spindlePositions[instanceId];
        return {
            type: 'spindle',
            name: `锭子 ${pos.index + 1}`,
            description: '使用InstancedMesh实例化渲染的纺纱锭子，通过皮带带动高速旋转。',
            index: pos.index + 1,
            material: '竹木',
            height: '约30厘米'
        };
    }

    createYarns() {
        this.yarnGroup = new THREE.Group();
        this.yarnGroup.userData = { type: 'yarn', name: '纱线', description: '由32个锭子纺出的纱线，汇集到上方导纱装置。' };

        const yarnMaterial = new THREE.LineBasicMaterial({
            color: 0xf5deb3,
            transparent: true,
            opacity: 0.8
        });

        this.yarnLines = [];
        const SEGMENTS = 6;

        for (let i = 0; i < this.spindleCount; i++) {
            const pos = this.spindlePositions[i];
            const positions = new Float32Array((SEGMENTS + 1) * 3);

            for (let s = 0; s <= SEGMENTS; s++) {
                const t = s / SEGMENTS;
                const sx = pos.x;
                const sy = pos.y + 0.9 + t * 2.0;
                const sz = pos.z * (1 - t);
                positions[s * 3] = sx;
                positions[s * 3 + 1] = sy;
                positions[s * 3 + 2] = sz;
            }

            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setDrawRange(0, SEGMENTS + 1);

            const line = new THREE.Line(geometry, yarnMaterial.clone());
            line.userData = { spindleIndex: i, basePos: { ...pos }, segments: SEGMENTS };
            this.yarnLines.push(line);
            this.yarnGroup.add(line);
        }

        this.group.add(this.yarnGroup);
    }

    updateYarnsLazy(time, speedFactor) {
        if (!this.showYarn) return;

        this.yarnUpdateCounter++;
        if (this.yarnUpdateCounter < this.yarnUpdateInterval) return;
        this.yarnUpdateCounter = 0;

        for (let i = 0; i < this.yarnLines.length; i++) {
            const line = this.yarnLines[i];
            const userData = line.userData;
            const base = userData.basePos;
            const segments = userData.segments;
            const positions = line.geometry.attributes.position.array;
            const waveOffset = i * 0.3;

            for (let s = 0; s <= segments; s++) {
                const t = s / segments;
                const wave = Math.sin(time * 3 + waveOffset + t * 2) * 0.05 * speedFactor;
                positions[s * 3] = base.x + wave * (1 - t) * 0.5;
                positions[s * 3 + 1] = base.y + 0.9 + t * 2.0 + wave * 0.2;
                positions[s * 3 + 2] = base.z * (1 - t) + wave * 0.15;
            }
            line.geometry.attributes.position.needsUpdate = true;
        }
    }

    update(delta, wheelSpeed) {
        this.time += delta;
        const speedFactor = Math.min(wheelSpeed / 50, 1.5);

        this.wheelRotation += delta * (wheelSpeed * 0.1) * 0.2;
        if (this.wheelGroup) {
            this.wheelGroup.rotation.z = -this.wheelRotation;
        }

        if (this.mainShaft) {
            this.mainShaft.rotation.x = this.wheelRotation * 3.5;
        }

        const dummy = new THREE.Object3D();
        const totalSpindleDelta = delta * (wheelSpeed * 0.1) * 3.5;

        for (let i = 0; i < this.spindleCount; i++) {
            const pos = this.spindlePositions[i];
            this.spindleRotationAccum[i] += totalSpindleDelta * this.spindleBaseRotationSpeeds[i];
            const rot = this.spindleRotationAccum[i];

            for (let p = 0; p < this.instancedSpindleParts.length; p++) {
                const part = this.instancedSpindleParts[p];
                const yOffset = part.userData.partYOffset;
                dummy.position.set(pos.x, pos.y + yOffset, pos.z);
                dummy.rotation.set(0, rot, 0);
                dummy.scale.set(1, 1, 1);
                dummy.updateMatrix();
                part.setMatrixAt(i, dummy.matrix);
            }
        }

        this.instancedSpindleParts.forEach(inst => {
            inst.instanceMatrix.needsUpdate = true;
        });

        this.updateYarnsLazy(this.time, speedFactor);
    }

    setYarnVisible(visible) {
        this.showYarn = visible;
        this.yarnGroup.visible = visible;
    }

    getClickableObjects() {
        const objects = [];
        if (this.wheelGroup) objects.push(this.wheelGroup);
        if (this.frameGroup) objects.push(this.frameGroup);
        if (this.mainShaft) objects.push(this.mainShaft);
        if (this.yarnGroup) objects.push(this.yarnGroup);
        if (this.spindleGroup) objects.push(this.spindleGroup);
        objects.push(...this.instancedSpindleParts);
        return objects;
    }
}
