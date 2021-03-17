#![allow(warnings, unused)]
#![cfg(feature = "interchange")]

pub mod References_capnp {
    include!(concat!(env!("OUT_DIR"), "/References_capnp.rs"));
}
pub mod LogicalNetlist_capnp {
    include!(concat!(env!("OUT_DIR"), "/LogicalNetlist_capnp.rs"));
}
pub mod DeviceResources_capnp {
    include!(concat!(env!("OUT_DIR"), "/DeviceResources_capnp.rs"));
}
