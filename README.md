# E-commerce API

A comprehensive Django-based e-commerce API with hierarchical product categories, OpenID Connect authentication, SMS/email notifications, and full CI/CD pipeline.

## Features

- **Hierarchical Product Categories**: Unlimited depth category structure
- **OpenID Connect Authentication**: Secure customer authentication with JWT tokens
- **REST API**: Complete CRUD operations for products, orders, and customers
- **Notifications**: SMS via Africa's Talking and email notifications
- **Order Management**: Shopping cart, order processing, and status tracking
- **Testing**: 80%+ test coverage with unit and integration tests
- **CI/CD**: Automated testing, security scanning, and deployment
- **Containerization**: Docker and Kubernetes deployment ready

## Quick Start

### Local Development

1. **Clone the repository**
   \`\`\`bash
   git clone <repository-url>
   cd ecommerce-api
   \`\`\`

2. **Install dependencies**
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. **Set up environment variables**
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your configuration
   \`\`\`

4. **Run migrations**
   \`\`\`bash
   python manage.py migrate
   \`\`\`

5. **Create superuser**
   \`\`\`bash
   python manage.py createsuperuser
   \`\`\`

6. **Start development server**
   \`\`\`bash
   python manage.py runserver
   \`\`\`

### Docker Development

\`\`\`bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
\`\`\`

## API Documentation

### Authentication

The API uses JWT tokens for authentication. Obtain tokens via:

\`\`\`bash
POST /api/customers/login/
{
    "username": "your_username",
    "password": "your_password"
}
\`\`\`

Include the token in subsequent requests:
\`\`\`
Authorization: Bearer <your_access_token>
\`\`\`

### Core Endpoints

#### Products
- `GET /api/products/` - List products
- `POST /api/products/` - Create product (admin only)
- `GET /api/products/{id}/` - Get product details
- `PUT /api/products/{id}/` - Update product (admin only)
- `DELETE /api/products/{id}/` - Delete product (admin only)

#### Categories
- `GET /api/products/categories/` - List categories
- `POST /api/products/categories/` - Create category (admin only)
- `GET /api/products/categories/{id}/average-price/` - Get average price

#### Orders
- `GET /api/orders/` - List user's orders
- `POST /api/orders/` - Create order
- `GET /api/orders/{id}/` - Get order details

#### Cart
- `GET /api/orders/cart/` - Get cart contents
- `POST /api/orders/cart/add/` - Add item to cart
- `PUT /api/orders/cart/items/{id}/` - Update cart item
- `DELETE /api/orders/cart/items/{id}/` - Remove cart item

## Testing

\`\`\`bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration

# Check coverage
coverage report
\`\`\`

## Deployment

### Kubernetes

1. **Apply configurations**
   \`\`\`bash
   kubectl apply -f k8s/
   \`\`\`

2. **Update secrets**
   \`\`\`bash
   # Edit k8s/secrets.yaml with base64 encoded values
   kubectl apply -f k8s/secrets.yaml
   \`\`\`

### Docker

\`\`\`bash
# Build image
docker build -t ecommerce-api:latest .

# Run container
docker run -p 8000:8000 ecommerce-api:latest
\`\`\`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (True/False) | No |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `AFRICAS_TALKING_USERNAME` | Africa's Talking username | Yes |
| `AFRICAS_TALKING_API_KEY` | Africa's Talking API key | Yes |
| `EMAIL_HOST_USER` | SMTP email username | Yes |
| `EMAIL_HOST_PASSWORD` | SMTP email password | Yes |

## Architecture

\`\`\`
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Django API    │    │   PostgreSQL    │
│                 │────│                 │────│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Celery Worker │    │      Redis      │
                       │                 │────│                 │
                       └─────────────────┘    └─────────────────┘
\`\`\`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.
# eCommerce_service
