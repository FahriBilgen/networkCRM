package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.enums.ProjectStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NodeRequest {

    @NotNull(message = "Node type is required")
    private NodeType type;

    @NotBlank(message = "Name is required")
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
}
