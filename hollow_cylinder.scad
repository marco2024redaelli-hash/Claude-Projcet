// Hollow Cylinder - Cilindro Cavo
// Parametri personalizzabili

// Altezza del cilindro
height = 50;

// Raggio esterno
outer_radius = 20;

// Raggio interno (spessore parete = outer_radius - inner_radius)
inner_radius = 15;

// Risoluzione (numero di facce per approssimare il cerchio)
$fn = 100;

// Cilindro cavo: differenza tra cilindro esterno e cilindro interno
difference() {
    cylinder(h = height, r = outer_radius, center = true);
    cylinder(h = height + 1, r = inner_radius, center = true);
}
