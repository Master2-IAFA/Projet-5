
use cgmath::{Vector3, Vector4};

use embree;
use image;

const N: u32 = 64;

fn main() {
    let device = embree::Device::new();

    let mut scene = embree::Scene::new(&device);

    let mut tris = embree::TriangleMesh::unanimated(&device, 2, 4);
    {
        let mut verts = tris.vertex_buffer.map();
        let mut inds = tris.index_buffer.map();

        verts[0] = Vector4::new(-1.0, -1.0, -5.0, 0.0);
        verts[1] = Vector4::new(-0.5, 1.0, -5.0, 0.0);
        verts[2] = Vector4::new(0.5, 1.0, -3.0, 0.0);
        verts[3] = Vector4::new(1.0, -1.0, -3.0, 0.0);

        inds[0] = Vector3::new(0, 1, 2);
        inds[1] = Vector3::new(0, 2, 3);
    }
    {
        let verts = tris.vertex_buffer.map();
        let inds = tris.index_buffer.map();

        for i in 0..verts.len() {
            let v = verts[i];
            println!("v = {} {} {} {}", v.x, v.y, v.z, v.w);
        }

        for i in 0..inds.len() {
            let idx = inds[i];
            println!("idx = {} {} {}", idx.x, idx.y, idx.z);
        }
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
    
    let origin = Vector3::new(0.0, 0.0, 0.0);
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
                let depth = ray_hit.ray.tfar / 6.0;

                pixel.0 = [(depth * 255.0) as u8];
            } else {
                let mut pixel = img.get_pixel_mut(i, N - j - 1);

                pixel.0 = [51];
            }
        }
    }

    img.save("res/img.png").unwrap();
}
