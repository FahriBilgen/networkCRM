package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Data
@Builder
public class FavoritePathResponse {
    private UUID id;
    private UUID goalId;
    private String label;
    private List<UUID> nodeIds;
    private LocalDateTime createdAt;
}
