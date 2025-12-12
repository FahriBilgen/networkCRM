package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDate;
import java.util.List;

@Data
@Builder
public class NodeClassificationRequest {
    private String name;
    private String description;
    private String notes;
    private String sector;
    private List<String> tags;
    private Integer priority;
    private String status;
    private LocalDate dueDate;
    private LocalDate startDate;
    private LocalDate endDate;
}
