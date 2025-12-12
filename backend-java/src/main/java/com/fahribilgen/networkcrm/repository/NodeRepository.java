package com.fahribilgen.networkcrm.repository;

import com.fahribilgen.networkcrm.entity.Node;
import com.fahribilgen.networkcrm.enums.NodeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface NodeRepository extends JpaRepository<Node, UUID>, JpaSpecificationExecutor<Node> {
    List<Node> findByUserId(UUID userId);
    List<Node> findByUserIdAndType(UUID userId, NodeType type);
    boolean existsByUserIdAndNameIgnoreCase(UUID userId, String name);
}
