package com.fahribilgen.networkcrm.repository;

import com.fahribilgen.networkcrm.entity.Edge;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface EdgeRepository extends JpaRepository<Edge, UUID> {
    List<Edge> findBySourceNodeId(UUID sourceNodeId);
    List<Edge> findByTargetNodeId(UUID targetNodeId);
    List<Edge> findBySourceNode_User_Id(UUID userId);
}
