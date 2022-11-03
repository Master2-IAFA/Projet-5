use cgmath::{Vector3, Vector4};

use embree;
use image;
use tobj;

const N: u32 = 256;

fn main() {
    let device = embree::Device::new();

    let mut scene = embree::Scene::new(&device);

    let mut opt = tobj::LoadOptions::default();
    opt.triangulate = true;
    let (models, _) = tobj::load_obj(
        "/home/lowin/Documents/assets/common-3d-test-models/data/stanford-bunny.obj",
        &opt,
    )
    .unwrap();

    println!("nb models: {}", models.len());

    let model = &models[0];
    let mut tris = embree::TriangleMesh::unanimated(
        &device,
        model.mesh.indices.len() / 3,
        model.mesh.positions.len() / 3,
    );

    let mut verts = tris.vertex_buffer.map();
    let mut inds = tris.index_buffer.map();

    for i in 0..(model.mesh.positions.len() / 3) {
        let idx = i * 3;
        let p = &model.mesh.positions;
        verts[i] = Vector4::new(p[idx], p[idx + 1], p[idx + 2], 0.0);
    }

    for i in 0..(model.mesh.indices.len() / 3) {
        let idx = i * 3;
        let j = &model.mesh.indices;
        inds[i] = Vector3::new(j[idx], j[idx + 1], j[idx + 2]);
    }


    let mut geom = embree::Geometry::Triangle(tris);
    geom.commit();

    scene.attach_geometry(geom);
    let scene = scene.commit();

    let mut img = image::GrayImage::new(N, N);

    let fov = f32::to_radians(45.0);
    let vp_w = 2.0;
    let vp_h = 2.0;
    let focal_length = (vp_w / 2.0) / f32::tan(fov);

    let origin = Vector3::new(0.0, 0.1, 0.2);
    let view_dir = Vector3::new(0.0, 0.0, -1.0);
    let right = Vector3::new(1.0, 0.0, 0.0) * vp_w;
    let up = Vector3::new(0.0, 1.0, 0.0) * vp_h;

    let view = (view_dir * focal_length) - right / 2.0 - up / 2.0;

    let mut ctx = embree::IntersectContext::coherent();

    for i in 0..N {
        for j in 0..N {
            let x = (i as f32) / (N - 1) as f32;
            let y = (j as f32) / (N - 1) as f32;

            let ray_dir = view + x * right + y * up;

            let ray = embree::Ray::new(origin, ray_dir);
            let mut ray_hit = embree::RayHit::new(ray);

            scene.intersect(&mut ctx, &mut ray_hit);

            if ray_hit.hit.hit() {
                let mut pixel = img.get_pixel_mut(i, N - j - 1);

                // Need a solution to replace 6.0 by something general.
                let depth = ray_hit.ray.tfar / 1.0;

                pixel.0 = [(depth * 255.0) as u8];
            } else {
                let mut pixel = img.get_pixel_mut(i, N - j - 1);

                pixel.0 = [51];
            }
        }
    }

    img.save("res/img.png").unwrap();
}
