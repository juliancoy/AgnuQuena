// Native OpenCASCADE solid for reliable tetrahedral FEA meshing.
SetFactory("OpenCASCADE");

id = 17.5;
od = 20.5;
length = 369.265;

Cylinder(1) = {0, 0, 0, 0, 0, length, od / 2};
Cylinder(2) = {0, 0, -0.1, 0, 0, length + 0.2, id / 2};
BooleanDifference(3) = { Volume{1}; Delete; }{ Volume{2}; Delete; };

// Tapered ergonomic pads: 3 mm radial land at their base, 2 mm at the face.
Cone(30) = {7.75, 0, 306.6445, 3.15, 0, 0, (10.10 + 6) / 2, (10.10 + 4) / 2};
Cone(31) = {7.75, 0, 268.6588, 3.15, 0, 0, (10.35 + 6) / 2, (10.35 + 4) / 2};
Cone(32) = {7.75, 0, 245.3211, 3.15, 0, 0, (9.75 + 6) / 2, (9.75 + 4) / 2};
Cone(33) = {7.75, 0, 211.8042, 3.50, 0, 0, (11.10 + 6) / 2, (11.10 + 4) / 2};
Cone(34) = {7.75, 0, 180.6708, 3.50, 0, 0, (11.10 + 6) / 2, (11.10 + 4) / 2};
Cone(35) = {7.75, 0, 152.9138, 3.15, 0, 0, (11.13 + 6) / 2, (11.13 + 4) / 2};
BooleanUnion(4) = { Volume{3}; Delete; }{ Volume{30:35}; Delete; };

// Circular acoustic openings extend only from the bore center through the pad.
Cylinder(10) = {0, 0, 306.6445, 14, 0, 0, 10.10 / 2};
Cylinder(11) = {0, 0, 268.6588, 14, 0, 0, 10.35 / 2};
Cylinder(12) = {0, 0, 245.3211, 14, 0, 0, 9.75 / 2};
Cylinder(13) = {0, 0, 211.8042, 14, 0, 0, 11.10 / 2};
Cylinder(14) = {0, 0, 180.6708, 14, 0, 0, 11.10 / 2};
Cylinder(15) = {0, 0, 152.9138, 14, 0, 0, 11.13 / 2};

BooleanDifference(20) = { Volume{4}; Delete; }{ Volume{10:15}; Delete; };
Physical Volume("FLUTE") = {20};

Mesh.MeshSizeMin = 0.65;
Mesh.MeshSizeMax = 1.8;
Mesh.MeshSizeFromCurvature = 18;
Mesh.Algorithm3D = 10;
Mesh.Optimize = 1;
Mesh.MshFileVersion = 2.2;
