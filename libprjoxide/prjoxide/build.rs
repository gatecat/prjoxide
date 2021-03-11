fn main() {
    capnpc::CompilerCommand::new()
        .default_parent_module(vec!["schema".into()])
        .src_prefix("../../3rdparty/fpga-interchange-schema/interchange/")
        .file("../../3rdparty/fpga-interchange-schema/interchange/References.capnp")
        .run().expect("schema compiler command");
    capnpc::CompilerCommand::new()
        .default_parent_module(vec!["schema".into()])
        .src_prefix("../../3rdparty/fpga-interchange-schema/interchange/")
        .file("../../3rdparty/fpga-interchange-schema/interchange/LogicalNetlist.capnp")
        .run().expect("schema compiler command");
    capnpc::CompilerCommand::new()
        .default_parent_module(vec!["schema".into()])
        .src_prefix("../../3rdparty/fpga-interchange-schema/interchange/")
        .file("../../3rdparty/fpga-interchange-schema/interchange/DeviceResources.capnp")
        .run().expect("schema compiler command");
}
