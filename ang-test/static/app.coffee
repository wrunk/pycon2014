class Main
  constructor: (canvas_element) ->
    @scene = new THREE.Scene()
    @renderer = new THREE.WebGLRenderer
      antialias: true
      canvas: canvas_element

    @camera = new THREE.PerspectiveCamera 45, window.innerWidth / window.innerHeight, 1, 10000
    @projector = new THREE.Projector()

    @mouse2D = new THREE.Vector3(0, 10000, 0.5)
    @normalMatrix = new THREE.Matrix3()

    @objects = []  # the cube objects holder
    @isCtrlDown = false
    @theta = 45 * 0.5
    @rollOverMesh = null

    window.addEventListener "resize", @onWindowResize, false

  render: () ->
    @theta += @mouse2D.x * 1.5  if @isCtrlDown
    @raycaster = @projector.pickingRay(@mouse2D.clone(), @camera)
    intersects = @raycaster.intersectObjects(@objects)
    if intersects.length > 0
      intersector = @getRealIntersector(intersects)
      if intersector
        @setVoxelPosition intersector
        @rollOverMesh.position = @voxelPosition

    @camera.position.x = 1400 * Math.sin(THREE.Math.degToRad(@theta))
    @camera.position.z = 1400 * Math.cos(THREE.Math.degToRad(@theta))
    @camera.lookAt @scene.position

    @renderer.render @scene, @camera

  onWindowResize: () =>
    @camera.aspect = window.innerWidth / window.innerHeight
    @camera.updateProjectionMatrix()
    @renderer.setSize window.innerWidth, window.innerHeight

  getRealIntersector: (intersects) ->
    i = undefined
    i = 0
    while i < intersects.length
      intersector = intersects[i]
      return intersector  if intersector.object isnt @rollOverMesh
      i += 1

  setVoxelPosition: (intersector) ->
    @normalMatrix.getNormalMatrix intersector.object.matrixWorld
    tmpVec = new THREE.Vector3()
    tmpVec.copy intersector.face.normal
    tmpVec.applyMatrix3(@normalMatrix).normalize()

    @voxelPosition = new THREE.Vector3()
    @voxelPosition.addVectors intersector.point, tmpVec
    @voxelPosition.divideScalar(50).floor().multiplyScalar(50).addScalar 25


  onDocumentMouseMove: (event) =>
    @mouse2D.x = (event.clientX / window.innerWidth) * 2 - 1
    @mouse2D.y = -(event.clientY / window.innerHeight) * 2 + 1

  onDocumentMouseDown: (event) =>
    intersects = @raycaster.intersectObjects(@objects)
    if intersects.length > 0
      intersector = @getRealIntersector(intersects)

      # delete cube
      if @isShiftDown
        if intersector.object isnt @plane
          @scene.remove intersector.object
          @objects.splice @objects.indexOf(intersector.object), 1
      else
        # create cube
        intersector = @getRealIntersector(intersects)
        @voxelPosition = @setVoxelPosition(intersector)
        voxel = new THREE.Mesh(@cubeGeo, @cubeMaterial)
        voxel.position.copy @voxelPosition
        voxel.matrixAutoUpdate = false
        voxel.updateMatrix()
        @scene.add voxel
        @objects.push voxel

  onDocumentKeyDown: (event) =>
    switch event.keyCode
      when 16
        @isShiftDown = true
      when 17
        @isCtrlDown = true

  onDocumentKeyUp: (event) =>
    switch event.keyCode
      when 16
        @isShiftDown = false
      when 17
        isCtrlDown = false

  init: () ->
    i = undefined
    size = 500
    step = 50
    geometry = undefined
    material = undefined
    line = undefined
    ambientLight = undefined
    directionalLight = undefined

    #    container = document.createElement( 'div' );
    #    document.body.appendChild( container );
    #    var info = document.createElement( 'div' );
    #    info.style.position = 'absolute';
    #    info.style.top = '10px';
    #    info.style.width = '100%';
    #    info.style.textAlign = 'center';
    #    info.innerHTML = '<a href="http://threejs.org" target="_blank">three.js</a> - voxel painter - webgl<br><strong>click</strong>: add voxel, <strong>shift + click</strong>: remove voxel, <strong>control</strong>: rotate';
    #    container.appendChild( info );
    @camera.position.y = 800

    # roll-over helpers
    rollOverGeo = new THREE.BoxGeometry(50, 50, 50)
    rollOverMaterial = new THREE.MeshBasicMaterial(
      color: 0xff0000
      opacity: 0.5
      transparent: true
    )
    @rollOverMesh = new THREE.Mesh(rollOverGeo, rollOverMaterial)
    @scene.add @rollOverMesh

    # cubes
    @cubeGeo = new THREE.BoxGeometry(50, 50, 50)
    @cubeMaterial = new THREE.MeshLambertMaterial(
      color: 0xfeb74c
      ambient: 0x00ff80
      shading: THREE.FlatShading
      map: THREE.ImageUtils.loadTexture("/static/square-outline-textured.png")
    )
    @cubeMaterial.ambient = @cubeMaterial.color


    # grid
    geometry = new THREE.Geometry()
    i = -size
    while i <= size
      geometry.vertices.push new THREE.Vector3(-size, 0, i)
      geometry.vertices.push new THREE.Vector3(size, 0, i)
      geometry.vertices.push new THREE.Vector3(i, 0, -size)
      geometry.vertices.push new THREE.Vector3(i, 0, size)
      i += step
    material = new THREE.LineBasicMaterial(
      color: 0x000000
      opacity: 0.2
      transparent: true
    )
    line = new THREE.Line(geometry, material)
    line.type = THREE.LinePieces
    @scene.add line

    @plane = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000), new THREE.MeshBasicMaterial())
    @plane.rotation.x = -Math.PI / 2
    @plane.visible = false
    @scene.add @plane

    @objects.push @plane

    # Lights
    ambientLight = new THREE.AmbientLight(0x606060)
    @scene.add ambientLight

    directionalLight = new THREE.DirectionalLight(0xffffff)
    directionalLight.position.set(1, 0.75, 0.5).normalize()
    @scene.add directionalLight

    @renderer.setClearColor 0xf0f0f0
    @renderer.setSize 500, 500

    #  renderer.setSize( window.innerWidth, window.innerHeight );
    #
    #  container.appendChild( renderer.domElement );
    #
    #  stats = new Stats();
    #  stats.domElement.style.position = 'absolute';
    #  stats.domElement.style.top = '0px';
    #  container.appendChild( stats.domElement );
    document.addEventListener "mousemove", @onDocumentMouseMove, false
    document.addEventListener "mousedown", @onDocumentMouseDown, false
    document.addEventListener "keydown", @onDocumentKeyDown, false
    document.addEventListener "keyup", @onDocumentKeyUp, false


$(document).ready ->
  window.app = new Main document.getElementById("game")
  app.init()
  window.animate = ->
    requestAnimationFrame animate
    window.app.render()

  window.animate()
  return @