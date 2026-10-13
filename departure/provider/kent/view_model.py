from departure.provider.nexus import view_model as nexus_view_model


# Inherits all behaviour from the Nexus view model, including its handling of
# board connection failures (`except grpc.RpcError`, logged not raised).
class ViewModelKentBus_192_32_3_Rows_To_ProtocolBuffers(
    nexus_view_model.ViewModelNexusBus_192_32_3_Rows_To_ProtocolBuffers
):
    # one more 6px character than Nexus, so Kent destinations are cut off later
    DESTINATION_MAX_WIDTH = 101
