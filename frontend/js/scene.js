class SceneManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.clock = new THREE.Clock();
        this.isRotating = true;
        this.wheelSpeed = 50;
        this.targetWheelSpeed = 50;
        
        this.init();
        this.createLights();
        this.createGround();
        this.createWater();
        this.animate();
        this.addEventListeners();
    }

    init() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0f3460);
        this.scene.fog = new THREE.Fog(0x0f3460, 20, 80);

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        this.camera.position.set(15, 10, 15);
        this.camera.lookAt(0, 3, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);
    }

    createLights() {
        const ambientLight = new THREE.AmbientLight(0x404060, 0.4);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 10);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 100;
        directionalLight.shadow.camera.left = -20;
        directionalLight.shadow.camera.right = 20;
        directionalLight.shadow.camera.top = 20;
        directionalLight.shadow.camera.bottom = -20;
        this.scene.add(directionalLight);

        const pointLight = new THREE.PointLight(0xff6b6b, 0.5, 30);
        pointLight.position.set(-5, 8, 5);
        this.scene.add(pointLight);
    }

    createGround() {
        const groundGeometry = new THREE.PlaneGeometry(60, 60);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: 0x2d4a3e,
            roughness: 0.9,
            metalness: 0.1
        });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);

        const gridHelper = new THREE.GridHelper(60, 60, 0x1a3a2a, 0x1a3a2a);
        gridHelper.position.y = 0.01;
        this.scene.add(gridHelper);
    }

    createWater() {
        this.waterParticles = [];
        this.waterGroup = new THREE.Group();
        this.scene.add(this.waterGroup);

        const particleCount = 200;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const velocities = [];

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = -15 + Math.random() * 10;
            positions[i * 3 + 1] = 3 + Math.random() * 4;
            positions[i * 3 + 2] = -3 + Math.random() * 6;
            velocities.push({
                x: 2 + Math.random() * 3,
                y: -0.5 - Math.random() * 1,
                z: (Math.random() - 0.5) * 0.5
            });
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.PointsMaterial({
            color: 0x64b5f6,
            size: 0.15,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });

        this.waterParticleSystem = new THREE.Points(geometry, material);
        this.waterGroup.add(this.waterParticleSystem);
        this.waterVelocities = velocities;

        const waterPlaneGeometry = new THREE.PlaneGeometry(20, 8);
        const waterPlaneMaterial = new THREE.MeshStandardMaterial({
            color: 0x2196f3,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });
        this.waterPlane = new THREE.Mesh(waterPlaneGeometry, waterPlaneMaterial);
        this.waterPlane.rotation.x = -Math.PI / 2;
        this.waterPlane.position.set(-10, 0.05, 0);
        this.waterGroup.add(this.waterPlane);
    }

    updateWater(delta) {
        if (!this.showWater) return;

        const positions = this.waterParticleSystem.geometry.attributes.position.array;
        const speedFactor = this.wheelSpeed / 50;

        for (let i = 0; i < positions.length / 3; i++) {
            positions[i * 3] += this.waterVelocities[i].x * delta * speedFactor;
            positions[i * 3 + 1] += this.waterVelocities[i].y * delta * speedFactor;
            positions[i * 3 + 2] += this.waterVelocities[i].z * delta;

            if (positions[i * 3] > 15 || positions[i * 3 + 1] < 0) {
                positions[i * 3] = -15 + Math.random() * 10;
                positions[i * 3 + 1] = 5 + Math.random() * 3;
                positions[i * 3 + 2] = -3 + Math.random() * 6;
            }
        }

        this.waterParticleSystem.geometry.attributes.position.needsUpdate = true;
    }

    setWaterVisible(visible) {
        this.showWater = visible;
        this.waterGroup.visible = visible;
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();

        this.wheelSpeed += (this.targetWheelSpeed - this.wheelSpeed) * 0.05;

        if (this.isRotating && this.spinningWheel) {
            this.spinningWheel.update(delta, this.wheelSpeed);
        }

        this.updateWater(delta);
        this.updateCamera(delta);

        this.renderer.render(this.scene, this.camera);
    }

    updateCamera(delta) {
    }

    addEventListeners() {
        window.addEventListener('resize', () => this.onWindowResize());
        
        this.renderer.domElement.addEventListener('click', (event) => this.onMouseClick(event));
        this.renderer.domElement.addEventListener('mousemove', (event) => this.onMouseMove(event));

        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        let spherical = { theta: Math.PI / 4, phi: Math.PI / 4, radius: 22 };
        const target = new THREE.Vector3(0, 3, 0);

        this.renderer.domElement.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });

        this.renderer.domElement.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            spherical.theta -= deltaX * 0.005;
            spherical.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.1, spherical.phi - deltaY * 0.005));

            previousMousePosition = { x: e.clientX, y: e.clientY };

            this.updateCameraPosition(spherical, target);
        });

        this.renderer.domElement.addEventListener('wheel', (e) => {
            e.preventDefault();
            spherical.radius = Math.max(8, Math.min(50, spherical.radius + e.deltaY * 0.02));
            this.updateCameraPosition(spherical, target);
        });

        this.cameraSpherical = spherical;
        this.cameraTarget = target;
        this.updateCameraPosition(spherical, target);
    }

    updateCameraPosition(spherical, target) {
        this.camera.position.x = target.x + spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
        this.camera.position.y = target.y + spherical.radius * Math.cos(spherical.phi);
        this.camera.position.z = target.z + spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
        this.camera.lookAt(target);
    }

    resetCamera() {
        this.cameraSpherical = { theta: Math.PI / 4, phi: Math.PI / 4, radius: 22 };
        this.cameraTarget = new THREE.Vector3(0, 3, 0);
        this.updateCameraPosition(this.cameraSpherical, this.cameraTarget);
    }

    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    onMouseClick(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);

        if (this.spinningWheel) {
            const intersects = this.raycaster.intersectObjects(this.spinningWheel.getClickableObjects(), true);
            if (intersects.length > 0) {
                const hit = intersects[0];

                if (hit.object.isInstancedMesh && hit.object.userData && hit.object.userData.isSpindleInstanced) {
                    const spindleInfo = this.spinningWheel.getSpindleInfo(hit.instanceId);
                    if (spindleInfo) {
                        this.onComponentClick(spindleInfo);
                        return;
                    }
                }

                const clickedObject = this.findClickableParent(hit.object);
                if (clickedObject && clickedObject.userData && clickedObject.userData.type) {
                    this.onComponentClick(clickedObject.userData);
                }
            }
        }
    }

    findClickableParent(object) {
        let current = object;
        while (current) {
            if (current.userData && current.userData.type) {
                return current;
            }
            current = current.parent;
        }
        return null;
    }

    onMouseMove(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        if (this.spinningWheel) {
            this.raycaster.setFromCamera(this.mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.spinningWheel.getClickableObjects(), true);
            
            if (intersects.length > 0) {
                this.renderer.domElement.style.cursor = 'pointer';
            } else {
                this.renderer.domElement.style.cursor = 'grab';
            }
        }
    }

    setSpinningWheel(wheel) {
        this.spinningWheel = wheel;
    }

    setWheelSpeed(speed) {
        this.targetWheelSpeed = speed;
    }

    toggleRotation() {
        this.isRotating = !this.isRotating;
        return this.isRotating;
    }

    onComponentClick(callback) {
        this.componentClickCallback = callback;
    }

    onComponentClick(userData) {
        if (this.componentClickCallback) {
            this.componentClickCallback(userData);
        }
    }
}
