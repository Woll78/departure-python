from departure.provider.nexus import view_model as nexus_view_model


# Inherits all behaviour from the Nexus view model, including its handling of
# board connection failures (`except grpc.RpcError`, logged not raised).
class ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers(
    nexus_view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers
):
    pass
