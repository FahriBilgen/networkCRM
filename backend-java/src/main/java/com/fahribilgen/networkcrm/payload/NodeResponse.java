package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.enums.ProjectStatus;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Data
@Builder
public class NodeResponse {
    private UUID id;
    private NodeType type;
    private String name;
    private String description;
    private String sector;
    private List<String> tags;
    private Integer relationshipStrength;
    private String company;
    private String role;
    private String linkedinUrl;
    private String notes;
    private Integer priority;
    private LocalDate dueDate;
    private LocalDate startDate;
    private LocalDate endDate;
    private ProjectStatus status;
    private Map<String, Object> properties;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
