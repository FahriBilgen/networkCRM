package com.fahribilgen.networkcrm.payload;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;
import java.util.UUID;

@Data
public class FavoritePathRequest {
    @NotNull
    private UUID goalId;

    @NotBlank
    private String label;

    @NotEmpty
    private List<UUID> nodeIds;
}
