import React, { useState } from 'react';
import { 
  ArrowRight, 
  BarChart3, 
  Database, 
  Zap, 
  Shield, 
  Star,
  Play,
  Check,
  Menu,
  X,
  Users,
  TrendingUp,
  Award,
  Twitter,
  Linkedin,
  Facebook,
  Instagram
} from 'lucide-react';
import Button from '@components/ui/Button';
import FigmaLogo from '@components/ui/FigmaLogo';

const Landing: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-white/80 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <FigmaLogo size="md" showText={true} />
            
            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center space-x-8">
              <a href="#home" className="text-foreground hover:text-primary transition-colors font-medium">Home</a>
              <a href="#features" className="text-foreground hover:text-primary transition-colors font-medium">Features</a>
              <a href="#solutions" className="text-foreground hover:text-primary transition-colors font-medium">Solutions</a>
              <a href="#pricing" className="text-foreground hover:text-primary transition-colors font-medium">Pricing</a>
              <a href="#about" className="text-foreground hover:text-primary transition-colors font-medium">About</a>
              <a href="#contact" className="text-foreground hover:text-primary transition-colors font-medium">Contact</a>
            </nav>
            
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" className="hidden md:inline-flex">
                Sign In
              </Button>
              <Button size="sm" className="bg-gradient-primary text-white border-0">
                Get Started Free
              </Button>
              
              {/* Mobile Menu Button */}
              <button
                className="lg:hidden p-2"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <Menu className="h-6 w-6" />
                )}
              </button>
            </div>
          </div>
          
          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="lg:hidden py-4 border-t border-border">
              <nav className="flex flex-col space-y-4">
                <a href="#home" className="text-foreground hover:text-primary transition-colors">Home</a>
                <a href="#features" className="text-foreground hover:text-primary transition-colors">Features</a>
                <a href="#solutions" className="text-foreground hover:text-primary transition-colors">Solutions</a>
                <a href="#pricing" className="text-foreground hover:text-primary transition-colors">Pricing</a>
                <a href="#about" className="text-foreground hover:text-primary transition-colors">About</a>
                <a href="#contact" className="text-foreground hover:text-primary transition-colors">Contact</a>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section id="home" className="relative overflow-hidden bg-gradient-to-br from-purple-50 to-indigo-50 py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="text-left">
              <div className="inline-flex items-center bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-6">
                🚀 New: Advanced AI Analytics Dashboard
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground mb-6 leading-tight">
                Transform Your Data Into{' '}
                <span className="gradient-text">Intelligent Insights</span>
              </h1>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                Harness the power of AI to unlock hidden patterns in your data. Make faster, 
                smarter decisions with our advanced analytics platform trusted by 10,000+ companies worldwide.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <Button size="lg" className="bg-gradient-primary text-white border-0 shadow-lg hover:shadow-xl transition-shadow">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button variant="outline" size="lg" className="group">
                  <Play className="mr-2 h-5 w-5 group-hover:text-primary" />
                  Watch Demo
                </Button>
              </div>
              <div className="flex items-center space-x-6 text-sm text-muted-foreground">
                <div className="flex items-center">
                  <Check className="h-4 w-4 text-green-500 mr-2" />
                  Free 14-day trial
                </div>
                <div className="flex items-center">
                  <Check className="h-4 w-4 text-green-500 mr-2" />
                  No credit card required
                </div>
                <div className="flex items-center">
                  <Check className="h-4 w-4 text-green-500 mr-2" />
                  Cancel anytime
                </div>
              </div>
            </div>
            
            <div className="relative">
              <div className="bg-white rounded-2xl shadow-2xl p-6">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-48 rounded-lg mb-4 flex flex-col items-center justify-center space-y-4">
                  <FigmaLogo size="lg" showText={false} className="filter brightness-0 invert" />
                  <div className="text-white text-sm font-medium">Analytics Dashboard</div>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Revenue Growth</span>
                    <span className="text-green-500 font-semibold">+24.5%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Active Users</span>
                    <span className="text-blue-500 font-semibold">125.3K</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Conversion Rate</span>
                    <span className="text-purple-500 font-semibold">8.2%</span>
                  </div>
                </div>
              </div>
              
              {/* Floating Elements */}
              <div className="absolute -top-4 -right-4 bg-white rounded-lg shadow-lg p-3">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-muted-foreground">Live Data</span>
                </div>
              </div>
              
              <div className="absolute -bottom-4 -left-4 bg-white rounded-lg shadow-lg p-3">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-blue-500" />
                  <span className="text-xs font-semibold">+15.2%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Background Elements */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
          <div className="absolute top-1/3 right-1/4 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
          <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl lg:text-4xl font-bold text-primary mb-2">{stat.number}</div>
                <div className="text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-muted/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
              ✨ Features
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-6">
              Everything You Need to{' '}
              <span className="gradient-text">Succeed</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Powerful tools and features designed to help you make better data-driven decisions
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow">
                <div className="w-14 h-14 bg-gradient-primary rounded-xl flex items-center justify-center mb-6">
                  <feature.icon className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-foreground mb-4">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solutions Section */}
      <section id="solutions" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-6">
              Built for Every{' '}
              <span className="gradient-text">Industry</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Tailored solutions for different sectors and use cases
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {solutions.map((solution, index) => (
              <div key={index} className="group cursor-pointer">
                <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-8 hover:shadow-lg transition-all duration-300 group-hover:scale-105">
                  <solution.icon className="h-12 w-12 text-primary mb-6" />
                  <h3 className="text-xl font-bold text-foreground mb-4">{solution.title}</h3>
                  <p className="text-muted-foreground mb-6">{solution.description}</p>
                  <div className="flex items-center text-primary font-medium">
                    Learn More
                    <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-muted/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-6">
              Loved by{' '}
              <span className="gradient-text">Thousands</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              See what our customers are saying about Suchana.ai
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="bg-white rounded-2xl p-8 shadow-lg">
                <div className="flex items-center mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-5 w-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-muted-foreground mb-6 leading-relaxed">"{testimonial.content}"</p>
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-gradient-primary rounded-full flex items-center justify-center mr-4">
                    <span className="text-white font-bold">{testimonial.author.charAt(0)}</span>
                  </div>
                  <div>
                    <div className="font-semibold text-foreground">{testimonial.author}</div>
                    <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-foreground mb-6">
              Simple,{' '}
              <span className="gradient-text">Transparent Pricing</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Choose the plan that fits your needs. All plans include a 14-day free trial.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricingPlans.map((plan, index) => (
              <div key={index} className={`rounded-2xl p-8 ${plan.featured ? 'bg-gradient-primary text-white shadow-2xl scale-105' : 'bg-white border border-border shadow-lg'}`}>
                <div className="text-center mb-8">
                  <h3 className={`text-2xl font-bold mb-4 ${plan.featured ? 'text-white' : 'text-foreground'}`}>{plan.name}</h3>
                  <div className="flex items-baseline justify-center">
                    <span className={`text-4xl font-bold ${plan.featured ? 'text-white' : 'text-foreground'}`}>${plan.price}</span>
                    <span className={`ml-2 ${plan.featured ? 'text-purple-100' : 'text-muted-foreground'}`}>/month</span>
                  </div>
                  <p className={`mt-4 ${plan.featured ? 'text-purple-100' : 'text-muted-foreground'}`}>{plan.description}</p>
                </div>
                
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center">
                      <Check className={`h-5 w-5 mr-3 ${plan.featured ? 'text-purple-200' : 'text-green-500'}`} />
                      <span className={plan.featured ? 'text-purple-100' : 'text-muted-foreground'}>{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <Button 
                  size="lg" 
                  className={`w-full ${plan.featured ? 'bg-white text-primary hover:bg-gray-100' : 'bg-gradient-primary text-white border-0'}`}
                >
                  {plan.featured ? 'Get Started' : 'Start Free Trial'}
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-purple-600 to-indigo-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">
            Ready to Transform Your Business?
          </h2>
          <p className="text-xl text-purple-100 mb-8 max-w-2xl mx-auto">
            Join thousands of companies already using Suchana.ai to make smarter, data-driven decisions.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="bg-white text-purple-600 hover:bg-gray-100 font-semibold">
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button variant="outline" size="lg" className="border-white text-white hover:bg-white hover:text-purple-600">
              Contact Sales
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-8">
            {/* Company Info */}
            <div className="lg:col-span-2">
              <div className="mb-4">
                <FigmaLogo size="lg" showText={true} />
              </div>
              <p className="text-gray-400 mb-6 max-w-md">
                Empowering businesses with intelligent analytics and AI-driven insights 
                to make better decisions and drive growth.
              </p>
              <div className="flex space-x-4">
                <Twitter className="h-6 w-6 text-gray-400 hover:text-white cursor-pointer transition-colors" />
                <Linkedin className="h-6 w-6 text-gray-400 hover:text-white cursor-pointer transition-colors" />
                <Facebook className="h-6 w-6 text-gray-400 hover:text-white cursor-pointer transition-colors" />
                <Instagram className="h-6 w-6 text-gray-400 hover:text-white cursor-pointer transition-colors" />
              </div>
            </div>
            
            {/* Quick Links */}
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Features</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Integrations</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">API</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Security</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Careers</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Press</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Documentation</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Contact</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors">Status</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-12 pt-8">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <p className="text-gray-400 text-sm">
                © 2025 Suchana.ai. All rights reserved.
              </p>
              <div className="flex space-x-6 mt-4 md:mt-0">
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">Privacy Policy</a>
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">Terms of Service</a>
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">Cookie Policy</a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

const stats = [
  { number: "10K+", label: "Active Users" },
  { number: "500M+", label: "Data Points Processed" },
  { number: "99.9%", label: "Uptime" },
  { number: "150+", label: "Countries" }
];

const features = [
  {
    icon: BarChart3,
    title: "Advanced Analytics",
    description: "Comprehensive data visualization tools with interactive dashboards, real-time charts, and customizable reports to track your key metrics."
  },
  {
    icon: Database,
    title: "Data Integration",
    description: "Connect seamlessly with 100+ data sources including databases, APIs, cloud services, and third-party applications."
  },
  {
    icon: Zap,
    title: "Real-time Processing",
    description: "Process millions of data points in real-time with our high-performance analytics engine and instant insights delivery."
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "Bank-level security with end-to-end encryption, GDPR compliance, and SOC 2 Type II certification for peace of mind."
  },
  {
    icon: Users,
    title: "Team Collaboration",
    description: "Share insights, create collaborative workspaces, and manage permissions with advanced team management features."
  },
  {
    icon: Award,
    title: "AI-Powered Insights",
    description: "Leverage machine learning algorithms to discover hidden patterns, predict trends, and get automated recommendations."
  }
];

const solutions = [
  {
    icon: TrendingUp,
    title: "Sales Analytics",
    description: "Track sales performance, forecast revenue, and optimize your sales funnel with detailed analytics and insights."
  },
  {
    icon: Users,
    title: "Customer Analytics",
    description: "Understand customer behavior, segment audiences, and improve retention with comprehensive customer data analysis."
  },
  {
    icon: BarChart3,
    title: "Marketing Analytics",
    description: "Measure campaign performance, ROI tracking, and optimize marketing spend across all channels and platforms."
  }
];

const testimonials = [
  {
    content: "Suchana.ai transformed how we analyze our data. The insights we get are incredible and have directly contributed to a 30% increase in our revenue.",
    author: "Sarah Johnson",
    role: "CEO, TechStart Inc."
  },
  {
    content: "The real-time analytics capabilities are game-changing. We can now make decisions based on live data instead of waiting for weekly reports.",
    author: "Michael Chen",
    role: "Data Director, GlobalCorp"
  },
  {
    content: "Implementation was seamless and the support team is outstanding. Within weeks, we had actionable insights that improved our operations significantly.",
    author: "Emma Rodriguez",
    role: "VP Analytics, RetailPlus"
  }
];

const pricingPlans = [
  {
    name: "Starter",
    price: 29,
    description: "Perfect for small teams getting started with data analytics",
    features: [
      "Up to 5 users",
      "10GB data storage",
      "Basic analytics",
      "Standard support",
      "Core integrations"
    ],
    featured: false
  },
  {
    name: "Professional",
    price: 99,
    description: "Advanced features for growing businesses and teams",
    features: [
      "Up to 25 users",
      "100GB data storage",
      "Advanced analytics",
      "Priority support",
      "All integrations",
      "Custom reports"
    ],
    featured: true
  },
  {
    name: "Enterprise",
    price: 299,
    description: "Full-featured solution for large organizations",
    features: [
      "Unlimited users",
      "1TB data storage",
      "AI-powered insights",
      "24/7 phone support",
      "Custom integrations",
      "White-label options"
    ],
    featured: false
  }
];

export default Landing;