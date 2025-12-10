package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;

import java.util.UUID;

public interface HierarchyService {
    void moveGoal(UUID goalId, UUID visionId, Integer sortOrder, User user);
    void moveProject(UUID projectId, UUID goalId, Integer sortOrder, User user);
}
