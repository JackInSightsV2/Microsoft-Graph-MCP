# Microsoft Graph MCP Server

An MCP (Model Context Protocol) server that provides AI assistants with secure access to Microsoft Graph API. Access user data, manage Azure AD resources, and perform administrative tasks through your AI assistant.

## Authentication Modes

### 🔍 Read-Only Mode (Device Code Flow)
- **No client secret required**
- Opens browser for user authentication
- Limited to user-delegated permissions
- Perfect for exploring data and read-only operations

### ✏️ App Registration Mode (Client Secret Flow)
- **Requires Azure AD app registration with client secret**
- Full administrative capabilities
- Application permissions for automated operations
- Can be scoped to specific permissions you need

## Quick Setup

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graph-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--init",
        "-e",
        "LOG_LEVEL=INFO",
        "-v",
        "graph-mcp-server:/tmp",
        "graph-mcp-server"
      ]
    }
  }
}
```

### Warp AI

Add to your MCP configuration:

```json
{
  "graph-mcp": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "-i",
      "--init",
      "-e",
      "LOG_LEVEL=INFO",
      "-v",
      "graph-mcp-server:/tmp",
      "graph-mcp-server"
    ],
    "env": {},
    "working_directory": null,
    "start_on_launch": true
  }
}
```

## Configuration Options

### Environment Variables

Set these in your MCP configuration or Docker environment:

- `AZURE_CLIENT_ID`: Your Azure AD application client ID
- `AZURE_TENANT_ID`: Your Azure AD tenant ID  
- `AZURE_CLIENT_SECRET`: Your client secret (optional, for app permissions)

### With Client Secret in MCP Config

```json
{
  "mcpServers": {
    "graph-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--init",
        "-e",
        "AZURE_CLIENT_ID=your-client-id",
        "-e",
        "AZURE_TENANT_ID=your-tenant-id",
        "-e",
        "AZURE_CLIENT_SECRET=your-client-secret",
        "-v",
        "graph-mcp-server:/tmp",
        "graph-mcp-server"
      ]
    }
  }
}
```

### Without Client Secret (Read-Only Mode)

```json
{
  "mcpServers": {
    "graph-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--init",
        "-e",
        "AZURE_CLIENT_ID=your-client-id",
        "-e",
        "AZURE_TENANT_ID=your-tenant-id",
        "-v",
        "graph-mcp-server:/tmp",
        "graph-mcp-server"
      ]
    }
  }
}
```

## Azure AD App Registration Setup

### Required App Registration Permissions

For **full write access**, configure these application permissions in your Azure AD app registration:

#### User Management
- `User.ReadWrite.All` - Read and write all users' full profiles
- `User.ManageIdentities.All` - Manage user identities
- `UserAuthenticationMethod.ReadWrite.All` - Read and write authentication methods

#### Group Management  
- `Group.ReadWrite.All` - Read and write all groups
- `GroupMember.ReadWrite.All` - Read and write group memberships

#### Device Management
- `Device.ReadWrite.All` - Read and write devices
- `DeviceManagementConfiguration.ReadWrite.All` - Read and write device configuration
- `DeviceManagementManagedDevices.ReadWrite.All` - Read and write managed devices

#### Application Management
- `Application.ReadWrite.All` - Read and write applications
- `AppRoleAssignment.ReadWrite.All` - Read and write app role assignments

#### Directory Management
- `Directory.ReadWrite.All` - Read and write directory data
- `RoleManagement.ReadWrite.Directory` - Read and write directory roles

#### Security & Compliance
- `SecurityEvents.ReadWrite.All` - Read and write security events
- `IdentityRiskEvent.ReadWrite.All` - Read and write identity risk events

#### Mail & Calendar (if needed)
- `Mail.ReadWrite` - Read and write mail
- `Calendars.ReadWrite` - Read and write calendars

#### Files & Sites (if needed)
- `Files.ReadWrite.All` - Read and write files
- `Sites.ReadWrite.All` - Read and write sites

### Scoped Permissions

You can scope your app registration to only the permissions you need. For example, for user management only:

- `User.ReadWrite.All`
- `Group.ReadWrite.All` 
- `Directory.Read.All`

## What It Does

- **User Management** - Create, update, delete, and manage Azure AD users
- **Group Management** - Manage groups and group memberships  
- **Device Management** - Monitor and manage devices
- **Application Management** - Manage Azure AD applications and service principals
- **Security Operations** - Access security events and risk data
- **Directory Operations** - Read and write directory information
- **Mail & Calendar** - Access user mail and calendar data (with permissions)

## Usage Examples

### Get Current User
```
graph_command(command="me")
```

### List All Users
```
graph_command(command="users")
```

### Create a User (requires client secret)
```
graph_command(
    command="users", 
    method="POST",
    data={
        "accountEnabled": true,
        "displayName": "John Doe",
        "mailNickname": "johndoe",
        "userPrincipalName": "johndoe@yourdomain.com",
        "passwordProfile": {
            "forceChangePasswordNextSignIn": true,
            "password": "TempPassword123!"
        }
    },
    client_secret="your-client-secret"
)
```

### Update User Properties
```
graph_command(
    command="users/user@domain.com",
    method="PATCH", 
    data={"jobTitle": "Senior Developer"}
)
```

## Local Development

```bash
git clone https://github.com/JackInSightsV2/Microsoft-Graph-MCP.git
cd Microsoft-Graph-MCP/graph-mcp-python
docker-compose up --build
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
